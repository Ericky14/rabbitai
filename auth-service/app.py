from fastapi import FastAPI, HTTPException
import jwt
from datetime import datetime, timedelta
import os

app = FastAPI(title="Auth Service")

class AuthService:
    def __init__(self):
        self.jwt_secret = os.getenv('JWT_SECRET', 'your-secret-key')
        self.jwt_algorithm = "HS256"
        self.users_db = {
            "test_user": {
                "id": "test_user",
                "email": "test@example.com",
                "name": "Test User"
            }
        }
    
    def create_jwt_token(self, user_data: dict) -> str:
        payload = {
            'user_id': user_data['id'],
            'email': user_data['email'],
            'name': user_data.get('name', ''),
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def verify_jwt_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

auth_service = AuthService()

@app.post("/auth/verify")
async def verify_token(token: str):
    """Verify JWT token - called by other services"""
    user_data = auth_service.verify_jwt_token(token)
    return {"valid": True, "user": user_data}

@app.post("/auth/login")
async def login(username: str, password: str):
    """Simple login for testing"""
    if username == "test" and password == "test":
        user_data = auth_service.users_db["test_user"]
        token = auth_service.create_jwt_token(user_data)
        return {"access_token": token, "token_type": "bearer", "user": user_data}
    raise HTTPException(status_code=401, detail="Invalid credentials")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
