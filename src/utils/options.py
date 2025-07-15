from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
API_KEY = os.getenv("API_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
key = os.getenv("FERNET_KEY")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SEND_TIME = os.getenv("SEND_TIME")

class RegisterRequest(BaseModel):
    username: str
    password: str

class RegisterRequestAccMt5(BaseModel):
    username: int
    password: str
    server: str