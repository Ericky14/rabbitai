import boto3
import json
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import requests
from config import Config

security = HTTPBearer()

class AuthService:
    def __init__(self):
        self.cognito_client = boto3.client(
            'cognito-idp',
            endpoint_url=Config.AWS_ENDPOINT_URL,
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_DEFAULT_REGION
        )
    
    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        try:
            # In production, verify JWT with Cognito
            # For local development, simplified verification
            token = credentials.credentials
            
            # Decode token (simplified for local)
            payload = jwt.get_unverified_claims(token)
            user_id = payload.get('sub')
            email = payload.get('email')
            
            return {
                'user_id': user_id,
                'email': email
            }
            
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    async def google_auth_callback(self, code: str):
        """Handle Google OAuth callback"""
        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'client_id': Config.GOOGLE_CLIENT_ID,
            'client_secret': Config.GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': 'http://localhost:8080/auth/google/callback'
        }
        
        token_response = requests.post(token_url, data=token_data)
        tokens = token_response.json()
        
        # Get user info from Google
        user_info_url = f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={tokens['access_token']}"
        user_response = requests.get(user_info_url)
        user_data = user_response.json()
        
        # Store/update user in Cognito
        user_id = await self._create_or_update_user(user_data)
        
        return {
            'user_id': user_id,
            'email': user_data['email'],
            'name': user_data['name']
        }
    
    async def _create_or_update_user(self, user_data):
        """Create or update user in Cognito"""
        try:
            # Simplified for local development
            return user_data['id']
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"User creation failed: {str(e)}")

auth_service = AuthService()