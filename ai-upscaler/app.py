from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import boto3
from config import Config
import uuid
import json
from auth import auth_service
from analytics import analytics_client
from metrics import metrics
import time

app = FastAPI(title="AI Upscaler API")

# Initialize AWS clients
s3_client = boto3.client(
    's3',
    endpoint_url=Config.AWS_ENDPOINT_URL,
    aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
    region_name=Config.AWS_DEFAULT_REGION
)

lambda_client = boto3.client(
    'lambda',
    endpoint_url=Config.AWS_ENDPOINT_URL,
    aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
    region_name=Config.AWS_DEFAULT_REGION
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    metrics.record_api_request(
        method=request.method,
        endpoint=request.url.path,
        duration=duration,
        status=response.status_code
    )
    
    return response

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/upscale")
async def upscale_image(
    file: UploadFile = File(...),
    user: dict = Depends(auth_service.verify_token)
):
    try:
        start_time = time.time()
        job_id = str(uuid.uuid4())
        
        # Record file upload metric
        metrics.record_file_upload(file.content_type)
        
        # Upload to S3 input bucket
        s3_key = f"input/{job_id}/{file.filename}"
        s3_client.upload_fileobj(
            file.file,
            Config.S3_INPUT_BUCKET,
            s3_key
        )
        
        # Log analytics
        await analytics_client.log_upscale_request(
            user['user_id'], job_id, file.size, file.content_type
        )
        
        # Invoke Lambda function
        lambda_start = time.time()
        payload = {
            'job_id': job_id,
            's3_input_key': s3_key
        }
        
        response = lambda_client.invoke(
            FunctionName=Config.UPSCALER_LAMBDA_FUNCTION,
            InvocationType='Event',  # Async
            Payload=json.dumps(payload)
        )
        
        lambda_duration = time.time() - lambda_start
        metrics.record_lambda_invocation(
            Config.UPSCALER_LAMBDA_FUNCTION,
            lambda_duration,
            'success' if response['StatusCode'] == 202 else 'error'
        )
        
        return JSONResponse({
            "job_id": job_id,
            "status": "queued",
            "user_id": user['user_id']
        })
        
    except Exception as e:
        metrics.record_lambda_error(Config.UPSCALER_LAMBDA_FUNCTION, type(e).__name__)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/google")
async def google_auth():
    """Redirect to Google OAuth"""
    google_auth_url = f"https://accounts.google.com/o/oauth2/auth?client_id={Config.GOOGLE_CLIENT_ID}&redirect_uri=http://localhost:8080/auth/google/callback&scope=openid email profile&response_type=code"
    return {"auth_url": google_auth_url}

@app.get("/auth/google/callback")
async def google_auth_callback(code: str):
    """Handle Google OAuth callback"""
    user_data = await auth_service.google_auth_callback(code)
    return user_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)


