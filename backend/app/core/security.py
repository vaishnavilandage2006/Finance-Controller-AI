from datetime import datetime,timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException,status
from .config import settings
pwd=CryptContext(schemes=["argon2"],deprecated="auto")
def hash_password(p): return pwd.hash(p)
def verify_password(p,h): return pwd.verify(p,h)
def create_token(email): return jwt.encode({"sub":email,"exp":datetime.utcnow()+timedelta(hours=8)},settings.jwt_secret,algorithm="HS256")
def decode_token(token):
    try: return jwt.decode(token,settings.jwt_secret,algorithms=["HS256"])
    except JWTError: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid or expired token")
