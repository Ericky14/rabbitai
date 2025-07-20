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
from config import Config
import os

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Upscaler Service")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8080"],
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

@app.post("/process")
async def process_upscale(job_data: dict):
    """Process upscale job using Real-ESRGAN"""
    try:
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
        
    except Exception as e:
        print(f"Error processing job {job_id}: {str(e)}")
        return {
            'job_id': job_id,
            'status': 'failed',
            'error': str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)
