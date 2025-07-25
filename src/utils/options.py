from pydantic import BaseModel
from dotenv import load_dotenv
import os
from sqlalchemy.inspection import inspect

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
SEND_TIME_UPDATE_SWAP_SUMMER = os.getenv("SEND_TIME_UPDATE_SWAP_SUMMER")
SEND_TIME_UPDATE_SWAP_WINTER = os.getenv("SEND_TIME_UPDATE_SWAP_WINTER")

class RegisterRequest(BaseModel):
    username: str
    password: str

class RegisterRequestAccMt5(BaseModel):
    username: int
    password: str
    server: str

def object_as_dict(obj):
    return {
        c.key: getattr(obj, c.key)
        for c in inspect(obj).mapper.column_attrs
    }