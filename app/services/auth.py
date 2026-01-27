import os
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

def verify_password(plain_password: str, hashed_password: str):
    """Verify a plain password against a hashed password using direct bcrypt."""
    try:
        # Bcrypt 4.0.0+ requires bytes for both arguments
        # If hashed_password is a string, encode it
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        
        # Plain password must be encoded
        password_bytes = plain_password.encode('utf-8')
        
        # Ensure it's not too long for bcrypt
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
            
        return bcrypt.checkpw(password_bytes, hashed_password)
    except Exception as e:
        print(f"❌ [AUTH] Password verification error: {e}")
        return False

def get_password_hash(password: str):
    """Generate a bcrypt hash for a plain password."""
    # Bcrypt has a 72-byte limit. We truncate to prevent ValueError in newer bcrypt versions.
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload if payload.get("exp") >= datetime.utcnow().timestamp() else None
    except JWTError:
        return None
