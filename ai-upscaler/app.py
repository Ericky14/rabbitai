
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import boto3
import httpx
from config import Config
import uuid
import json
from analytics import analytics_client
from metrics import metrics
import time

app = FastAPI(title="AI Upscaler API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize AWS clients
s3_client_config = {
    'aws_access_key_id': Config.AWS_ACCESS_KEY_ID,
    'aws_secret_access_key': Config.AWS_SECRET_ACCESS_KEY,
    'region_name': Config.AWS_DEFAULT_REGION
}

# Only use endpoint_url for local development
if Config.AWS_ENDPOINT_URL and 'localhost' in Config.AWS_ENDPOINT_URL:
    s3_client_config['endpoint_url'] = Config.AWS_ENDPOINT_URL

s3_client = boto3.client('s3', **s3_client_config)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to record API metrics"""
    start_time = time.time()
    method = request.method
    endpoint = str(request.url.path)
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    status = response.status_code
    
    # Record metrics
    metrics.record_api_request(method, endpoint, duration, status)
    
    return response

@app.get("/")
async def root():
    return {"message": "AI Upscaler API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/upscale")
async def upscale_image(file: UploadFile = File(...)):
    start_time = time.time()
    job_id = str(uuid.uuid4())
    
    try:
        # Upload file to S3
        file_content = await file.read()
        s3_input_key = f"input/{job_id}/{file.filename}"
        
        s3_client.put_object(
            Bucket=Config.S3_INPUT_BUCKET,
            Key=s3_input_key,
            Body=file_content,
            ContentType=file.content_type
        )
        
        # Call upscaler service
        upscaler_payload = {
            "job_id": job_id,
            "s3_input_key": s3_input_key
        }
        
        print(f"Calling upscaler service at: {Config.UPSCALER_SERVICE_URL}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{Config.UPSCALER_SERVICE_URL}/process",
                json=upscaler_payload,
                timeout=300.0
            )
        
        print(f"Upscaler response status: {response.status_code}")
        print(f"Upscaler response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Log analytics
            await analytics_client.log_upscale_completion(
                job_id, time.time() - start_time, "success"
            )
            
            # Record metrics
            metrics.record_file_upload(file.content_type or "unknown")
            
            return {
                "job_id": job_id,
                "status": "completed",
                "input_file": file.filename,
                "output_key": result['output_key'],
                "processing_time": time.time() - start_time
            }
        else:
            print(f"Upscaler service error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=500, detail=f"Processing failed: {response.text}")
            
    except Exception as e:
        print(f"Upload error: {str(e)}")
        await analytics_client.log_upscale_completion(
            job_id, time.time() - start_time, "failed"
        )
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/download/{job_id}")
async def download_upscaled_image(job_id: str):
    try:
        output_key = f"output/{job_id}/upscaled.jpg"
        
        # Generate presigned URL for download with localhost endpoint
        download_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': Config.S3_OUTPUT_BUCKET, 'Key': output_key},
            ExpiresIn=3600  # 1 hour
        )
        
        # Replace the internal Docker hostname with localhost for browser access
        download_url = download_url.replace('localstack:4566', 'localhost:4566')
        
        return {"download_url": download_url}
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)


