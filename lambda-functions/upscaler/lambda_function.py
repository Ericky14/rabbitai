import json
import boto3
import base64
from PIL import Image
import io

def lambda_handler(event, context):
    """
    Lambda function to upscale images
    """
    try:
        # Parse the event
        job_id = event['job_id']
        s3_input_key = event['s3_input_key']
        
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Download image from S3
        response = s3_client.get_object(
            Bucket='ai-upscaler-input',
            Key=s3_input_key
        )
        
        # Load and process image
        image_data = response['Body'].read()
        image = Image.open(io.BytesIO(image_data))
        
        # Simple upscaling (2x) - replace with actual AI model
        upscaled = image.resize((image.width * 2, image.height * 2), Image.LANCZOS)
        
        # Save upscaled image
        output_buffer = io.BytesIO()
        upscaled.save(output_buffer, format='JPEG', quality=95)
        output_buffer.seek(0)
        
        # Upload to output bucket
        output_key = f"output/{job_id}/upscaled.jpg"
        s3_client.put_object(
            Bucket='ai-upscaler-output',
            Key=output_key,
            Body=output_buffer.getvalue(),
            ContentType='image/jpeg'
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'job_id': job_id,
                'status': 'completed',
                'output_key': output_key
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'job_id': job_id,
                'status': 'failed',
                'error': str(e)
            })
        }