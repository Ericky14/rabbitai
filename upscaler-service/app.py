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
        tile=256,        # Smaller tiles for less memory, faster processing
        tile_pad=5,      # Reduced padding
        pre_pad=0,
        half=False,      # Keep False for CPU
        device='cpu'     # Explicitly set CPU device
    )
    return upsampler

# Load model at startup
print("Loading Real-ESRGAN model...")
upsampler = load_realesrgan_model()
print("Model loaded successfully!")

# Add model warming and caching
def warm_up_model():
    """Warm up the model with a small test image"""
    logger.info("Warming up Real-ESRGAN model...")
    try:
        # Create a small test image
        test_img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
        upsampler.enhance(test_img, outscale=4)
        logger.info("Model warmed up successfully")
    except Exception as e:
        logger.warning(f"Model warm-up failed: {e}")

# Warm up model at startup
print("Warming up model for faster processing...")
warm_up_model()
print("Model ready for processing!")

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
    """Process upscale job from queue with optimizations"""
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
        response = s3_client.get_object(
            Bucket=Config.S3_INPUT_BUCKET,
            Key=job_data['s3_input_key']
        )
        
        update_progress(30, "Loading and optimizing image")
        
        # Load and process image with optimizations
        image_data = response['Body'].read()
        image = Image.open(io.BytesIO(image_data))
        
        # Aggressive resizing for small instances
        max_dimension = 512  # Reduced from 1024 for faster processing
        original_size = image.size
        
        if max(image.size) > max_dimension:
            logger.info(f"Resizing large image from {image.size} to max {max_dimension}")
            # Use faster resampling method
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.BILINEAR)
            update_progress(40, "Resized for faster processing")
        
        # Convert to RGB if needed (remove alpha channel)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
            update_progress(45, "Optimized image format")
        
        # Convert to OpenCV format
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        update_progress(50, "AI upscaling (optimized)")
        logger.info(f"Starting optimized AI upscaling for image size: {img_cv.shape}")
        
        # Use optimized upscaling with smaller chunks
        def upscale_task():
            # Process in smaller chunks for memory efficiency
            height, width = img_cv.shape[:2]
            if height * width > 256 * 256:  # If image is large, process in chunks
                logger.info("Processing large image in chunks for memory efficiency")
                return upsampler.enhance(img_cv, outscale=4)
            else:
                return upsampler.enhance(img_cv, outscale=4)
        
        future = executor.submit(upscale_task)
        output, _ = future.result(timeout=180)  # Reduced timeout to 3 minutes
        logger.info("Optimized AI upscaling completed")
        
        update_progress(80, "Converting result")
        
        # Convert and save with optimized quality
        upscaled_rgb = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
        upscaled = Image.fromarray(upscaled_rgb)
        
        output_buffer = io.BytesIO()
        # Use progressive JPEG for faster loading
        upscaled.save(output_buffer, format='JPEG', quality=90, optimize=True, progressive=True)
        output_buffer.seek(0)
        
        update_progress(95, "Uploading result")
        
        # Upload to output bucket
        output_key = f"output/{job_id}/upscaled.jpg"
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
            "completed_at": time.time(),
            "original_size": original_size,
            "processing_time": time.time() - job_data.get('started_at', time.time())
        }))
        
        logger.info(f"Job {job_id} completed successfully")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error(f"Error processing job: {e}", exc_info=True)
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
