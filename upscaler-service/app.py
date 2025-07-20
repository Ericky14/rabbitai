from fastapi import FastAPI, HTTPException
import boto3
from PIL import Image
import io
import numpy as np
import cv2
import torch
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet
import json
import pika
import redis
import threading
from config import Config
import os
import time

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

# Initialize Real-ESRGAN model
def load_realesrgan_model():
    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    model_path = '/app/weights/RealESRGAN_x4plus.pth'
    
    upsampler = RealESRGANer(
        scale=4,
        model_path=model_path,
        model=model,
        tile=0,
        tile_pad=10,
        pre_pad=0,
        half=False  # Set to True if you have GPU
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
    connection = pika.BlockingConnection(pika.URLParameters(Config.RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue='upscale_jobs', durable=True)
    channel.basic_consume(
        queue='upscale_jobs',
        on_message_callback=process_upscale_job,
        auto_ack=False
    )
    print("Waiting for upscale jobs...")
    channel.start_consuming()

def process_upscale_job(ch, method, properties, body):
    """Process upscale job from queue"""
    try:
        job_data = json.loads(body)
        job_id = job_data['job_id']
        
        # Update status to processing
        redis_client.setex(f"job:{job_id}", 3600, json.dumps({
            "status": "processing",
            "started_at": time.time()
        }))
        
        # Process the image (existing logic)
        result = process_image(job_data)
        
        # Update status to completed
        redis_client.setex(f"job:{job_id}", 3600, json.dumps({
            "status": "completed",
            "output_key": result['output_key'],
            "completed_at": time.time()
        }))
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f"Error processing job: {e}")
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
consumer_thread = threading.Thread(target=setup_rabbitmq_consumer, daemon=True)
consumer_thread.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)
