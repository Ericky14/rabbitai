import requests
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import Config

security = HTTPBearer()

class AuthService:
    def __init__(self):
        self.auth_service_url = Config.AUTH_SERVICE_URL
    
    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        try:
            # Call auth service to verify token
            response = requests.post(
                f"{self.auth_service_url}/auth/verify",
                json={"token": credentials.credentials}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            data = response.json()
            return data["user"]
            
        except requests.RequestException:
            raise HTTPException(status_code=503, detail="Auth service unavailable")

auth_service = AuthService()
