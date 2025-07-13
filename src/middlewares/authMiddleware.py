from fastapi import Request, HTTPException
from src.utils.options import API_KEY
from passlib.context import CryptContext
from src.models.model import SessionLocal
from cryptography.fernet import Fernet
from src.utils.options import key

f = Fernet(key.encode())

# ✅ Middleware kiểm tra API key
def verify_api_key(request: Request):
    token = request.headers.get("X-API-KEY")
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

# Mã hóa
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(data: str) -> str:
    return pwd_context.hash(data)

def encrypt_password_mt5(data: str) -> str:
    return f.encrypt(data.encode()).decode()

def decrypt_password_mt5(data: str) -> str:
    return f.decrypt(data.encode()).decode()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()