from fastapi import FastAPI, HTTPException
import boto3
from PIL import Image
import io
import numpy as np
import cv2
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet
import json
import pika
import redis
import threading
from config import Config
import time
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Upscaler Service")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000", 
        "http://localhost:8080",
        "https://fastrabbitai.com",
        "https://api.fastrabbitai.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize clients
s3_client_config = {
    'aws_access_key_id': Config.AWS_ACCESS_KEY_ID,
    'aws_secret_access_key': Config.AWS_SECRET_ACCESS_KEY,
    'region_name': Config.AWS_DEFAULT_REGION
}

# Only use endpoint_url for local development
if Config.AWS_ENDPOINT_URL and 'localhost' in Config.AWS_ENDPOINT_URL:
    s3_client_config['endpoint_url'] = Config.AWS_ENDPOINT_URL

s3_client = boto3.client('s3', **s3_client_config)

redis_client = redis.from_url(Config.REDIS_URL)

# Create a thread pool for CPU-intensive tasks
executor = ThreadPoolExecutor(max_workers=2)

# Initialize Real-ESRGAN model with optimized settings
def load_realesrgan_model():
    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    model_path = '/app/weights/RealESRGAN_x4plus.pth'
    
    upsampler = RealESRGANer(
        scale=4,
        model_path=model_path,
        model=model,
        tile=512,        # Use tiling to reduce memory usage and improve speed
        tile_pad=10,
        pre_pad=0,
        half=False       # Keep False for CPU, True for GPU would be faster
    )
    return upsampler

# Load model at startup
print("Loading Real-ESRGAN model...")
upsampler = load_realesrgan_model()
print("Model loaded successfully!")

@app.get("/health")
async def health():
    return {"status": "healthy", "model": "Real-ESRGAN x4"}

def setup_rabbitmq_consumer():
    """Setup RabbitMQ consumer for upscale jobs"""
    logger.info(f"Attempting to connect to RabbitMQ: {Config.RABBITMQ_URL}")
    try:
        connection = pika.BlockingConnection(pika.URLParameters(Config.RABBITMQ_URL))
        channel = connection.channel()
        channel.queue_declare(queue='upscale_jobs', durable=True)
        logger.info("Successfully declared upscale_jobs queue")
        
        channel.basic_consume(
            queue='upscale_jobs',
            on_message_callback=process_upscale_job,
            auto_ack=False
        )
        logger.info("RabbitMQ consumer setup complete. Waiting for upscale jobs...")
        channel.start_consuming()
    except Exception as e:
        logger.error(f"Failed to setup RabbitMQ consumer: {e}")
        raise

def process_upscale_job(ch, method, properties, body):
    """Process upscale job from queue"""
    logger.info(f"Received message: {body}")
    try:
        job_data = json.loads(body)
        job_id = job_data['job_id']
        logger.info(f"Processing job {job_id}")
        
        # Update status to processing with progress
        def update_progress(progress, stage):
            logger.info(f"Job {job_id}: {stage} - {progress}%")
            redis_client.setex(f"job:{job_id}", 3600, json.dumps({
                "status": "processing",
                "progress": progress,
                "stage": stage,
                "started_at": time.time()
            }))
        
        update_progress(10, "Downloading image")
        
        # Download image from S3
        logger.info(f"Downloading from S3: {job_data['s3_input_key']}")
        response = s3_client.get_object(
            Bucket=Config.S3_INPUT_BUCKET,
            Key=job_data['s3_input_key']
        )
        
        update_progress(30, "Loading image")
        
        # Load and process image
        image_data = response['Body'].read()
        logger.info(f"Image data size: {len(image_data)} bytes")
        image = Image.open(io.BytesIO(image_data))
        
        # Resize if image is too large (for faster processing)
        max_dimension = 1024  # Limit input size
        if max(image.size) > max_dimension:
            logger.info(f"Resizing large image from {image.size}")
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            update_progress(35, "Resizing large image")
        
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        update_progress(50, "AI upscaling")
        logger.info(f"Starting AI upscaling for image size: {img_cv.shape}")
        
        # Submit CPU-intensive task to thread pool
        def upscale_task():
            return upsampler.enhance(img_cv, outscale=4)
        
        future = executor.submit(upscale_task)
        output, _ = future.result(timeout=300)  # 5 minute timeout
        logger.info("AI upscaling completed")
        
        update_progress(80, "Converting image")
        
        # Convert and save
        upscaled_rgb = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
        upscaled = Image.fromarray(upscaled_rgb)
        
        output_buffer = io.BytesIO()
        upscaled.save(output_buffer, format='JPEG', quality=95)
        output_buffer.seek(0)
        
        update_progress(95, "Uploading result")
        
        # Upload to output bucket
        output_key = f"output/{job_id}/upscaled.jpg"
        logger.info(f"Uploading to S3: {output_key}")
        s3_client.put_object(
            Bucket=Config.S3_OUTPUT_BUCKET,
            Key=output_key,
            Body=output_buffer.getvalue(),
            ContentType='image/jpeg'
        )
        
        # Update status to completed
        redis_client.setex(f"job:{job_id}", 3600, json.dumps({
            "status": "completed",
            "progress": 100,
            "output_key": output_key,
            "completed_at": time.time()
        }))
        
        logger.info(f"Job {job_id} completed successfully")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error(f"Error processing job: {e}", exc_info=True)
        # Update status to failed
        redis_client.setex(f"job:{job_id}", 3600, json.dumps({
            "status": "failed",
            "error": str(e),
            "failed_at": time.time()
        }))
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def process_image(job_data):
    """Extract the existing image processing logic"""
    job_id = job_data['job_id']
    s3_input_key = job_data['s3_input_key']
    
    # Download image from S3
    response = s3_client.get_object(
        Bucket=Config.S3_INPUT_BUCKET,
        Key=s3_input_key
    )
    
    # Load and process image
    image_data = response['Body'].read()
    image = Image.open(io.BytesIO(image_data))
    
    # Convert PIL to OpenCV format
    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    # Apply Real-ESRGAN upscaling
    print(f"Upscaling image for job {job_id}...")
    output, _ = upsampler.enhance(img_cv, outscale=4)
    
    # Convert back to PIL
    upscaled_rgb = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
    upscaled = Image.fromarray(upscaled_rgb)
    
    # Save upscaled image
    output_buffer = io.BytesIO()
    upscaled.save(output_buffer, format='JPEG', quality=95)
    output_buffer.seek(0)
    
    # Upload to output bucket
    output_key = f"output/{job_id}/upscaled.jpg"
    s3_client.put_object(
        Bucket=Config.S3_OUTPUT_BUCKET,
        Key=output_key,
        Body=output_buffer.getvalue(),
        ContentType='image/jpeg'
    )
    
    return {
        'job_id': job_id,
        'status': 'completed',
        'output_key': output_key,
        'model': 'Real-ESRGAN x4'
    }

# Start RabbitMQ consumer in background thread
logger.info("Starting RabbitMQ consumer thread...")
consumer_thread = threading.Thread(target=setup_rabbitmq_consumer, daemon=True)
consumer_thread.start()
logger.info("Consumer thread started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)
