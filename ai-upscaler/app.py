
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
import redis
import pika
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Upscaler API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "https://fastrabbitai.com",
        "https://www.fastrabbitai.com"
    ],
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

# Initialize Redis client
redis_client = redis.from_url(Config.REDIS_URL)

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

# Add RabbitMQ connection
def publish_to_queue(message, queue_name):
    """Publish message to RabbitMQ queue"""
    logger.info(f"Attempting to publish message to queue '{queue_name}': {message}")
    try:
        connection = pika.BlockingConnection(pika.URLParameters(Config.RABBITMQ_URL))
        logger.info(f"Connected to RabbitMQ: {Config.RABBITMQ_URL}")
        
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        logger.info(f"Queue '{queue_name}' declared successfully")
        
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
        )
        logger.info(f"Message published successfully to queue '{queue_name}'")
        connection.close()
        logger.info("RabbitMQ connection closed")
        
    except Exception as e:
        logger.error(f"Failed to publish message to RabbitMQ: {e}", exc_info=True)
        raise

@app.post("/upscale")
async def upscale_image(file: UploadFile = File(...)):
    start_time = time.time()
    job_id = str(uuid.uuid4())
    
    logger.info(f"Starting upscale job {job_id} for file: {file.filename}")
    
    try:
        # Upload file to S3
        file_content = await file.read()
        s3_input_key = f"input/{job_id}/{file.filename}"
        
        logger.info(f"Uploading file to S3: {s3_input_key}")
        s3_client.put_object(
            Bucket=Config.S3_INPUT_BUCKET,
            Key=s3_input_key,
            Body=file_content,
            ContentType=file.content_type
        )
        logger.info(f"File uploaded to S3 successfully")
        
        # Send job to RabbitMQ queue
        job_payload = {
            "job_id": job_id,
            "s3_input_key": s3_input_key,
            "filename": file.filename,
            "content_type": file.content_type,
            "created_at": time.time()
        }
        
        logger.info(f"Preparing to publish job to RabbitMQ: {job_payload}")
        
        # Publish to processing queue
        publish_to_queue(job_payload, 'upscale_jobs')
        logger.info(f"Job {job_id} published to upscale_jobs queue")
        
        # Set initial status in Redis
        redis_client.setex(f"job:{job_id}", 3600, json.dumps({
            "status": "queued",
            "created_at": time.time()
        }))
        logger.info(f"Job {job_id} status set to 'queued' in Redis")
        
        return {
            "job_id": job_id,
            "status": "queued",
            "input_file": file.filename
        }
        
    except Exception as e:
        logger.error(f"Upload error for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    try:
        status_data = redis_client.get(f"job:{job_id}")
        if not status_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return json.loads(status_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@app.get("/download/{job_id}")
async def download_upscaled_image(job_id: str):
    try:
        output_key = f"output/{job_id}/upscaled.jpg"
        
        # Generate presigned URL for download
        download_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': Config.S3_OUTPUT_BUCKET, 'Key': output_key},
            ExpiresIn=3600  # 1 hour
        )
        
        return {"download_url": download_url}
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")

@app.delete("/admin/queue/{queue_name}")
async def clear_queue(queue_name: str):
    """Clear all messages from a specific queue"""
    logger.info(f"Attempting to clear queue: {queue_name}")
    try:
        connection = pika.BlockingConnection(pika.URLParameters(Config.RABBITMQ_URL))
        channel = connection.channel()
        
        # Purge the queue
        method = channel.queue_purge(queue=queue_name)
        message_count = method.method.message_count
        
        connection.close()
        logger.info(f"Successfully cleared {message_count} messages from queue '{queue_name}'")
        
        return {
            "message": f"Cleared {message_count} messages from queue '{queue_name}'",
            "queue": queue_name,
            "messages_cleared": message_count
        }
        
    except Exception as e:
        logger.error(f"Failed to clear queue {queue_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear queue: {str(e)}")

@app.get("/admin/queues")
async def list_queues():
    """List all queues and their message counts"""
    logger.info("Fetching queue information")
    try:
        connection = pika.BlockingConnection(pika.URLParameters(Config.RABBITMQ_URL))
        channel = connection.channel()
        
        # Get queue info for known queues
        queues_info = []
        known_queues = ['upscale_jobs', 'analytics_events']
        
        for queue_name in known_queues:
            try:
                method = channel.queue_declare(queue=queue_name, passive=True)
                queues_info.append({
                    "name": queue_name,
                    "messages": method.method.message_count,
                    "consumers": method.method.consumer_count
                })
            except Exception as e:
                logger.warning(f"Queue {queue_name} not found or error: {e}")
        
        connection.close()
        
        return {
            "queues": queues_info,
            "total_queues": len(queues_info)
        }
        
    except Exception as e:
        logger.error(f"Failed to list queues: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list queues: {str(e)}")

@app.delete("/admin/queues/clear-all")
async def clear_all_queues():
    """Clear all messages from all known queues"""
    logger.info("Attempting to clear all queues")
    try:
        connection = pika.BlockingConnection(pika.URLParameters(Config.RABBITMQ_URL))
        channel = connection.channel()
        
        known_queues = ['upscale_jobs', 'analytics_events']
        results = []
        total_cleared = 0
        
        for queue_name in known_queues:
            try:
                method = channel.queue_purge(queue=queue_name)
                message_count = method.method.message_count
                total_cleared += message_count
                
                results.append({
                    "queue": queue_name,
                    "messages_cleared": message_count,
                    "status": "success"
                })
                logger.info(f"Cleared {message_count} messages from queue '{queue_name}'")
                
            except Exception as e:
                results.append({
                    "queue": queue_name,
                    "messages_cleared": 0,
                    "status": "error",
                    "error": str(e)
                })
                logger.error(f"Failed to clear queue {queue_name}: {e}")
        
        connection.close()
        
        return {
            "message": f"Cleared {total_cleared} total messages from {len(known_queues)} queues",
            "total_messages_cleared": total_cleared,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Failed to clear all queues: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear all queues: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)


