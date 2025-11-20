from pydantic import BaseModel
from dotenv import load_dotenv
import os
from sqlalchemy.inspection import inspect
import re
from typing import Literal

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
TOKEN_VPS = os.getenv("TOKEN_VPS")
API_VPS = os.getenv("API_VPS")

class RegisterRequest(BaseModel):
    username: str
    password: str

class RegisterRequestAccMt5(BaseModel):
    username: int
    password: str
    server: str

class UpdateRiskAccTransaction(BaseModel):
    id_Risk: int = None
    id_daily_risk: int = None
    id_acc: int
    monney_acc: int = None
    type_acc: Literal["QUY", "USD", "COPY", "DEPOSIT", "RECIPROCAL", "RECIPROCAL_ACC", "COM", "SWWING" ,"VAY", "DEMO", "BOOT_STRATEGY"] = None

def object_as_dict(obj):
    return {
        c.key: getattr(obj, c.key)
        for c in inspect(obj).mapper.column_attrs
    }

def replace_suffix_with_m(sym: str) -> str:
    # Lấy phần chữ cái và số chính (base symbol)
    base = re.match(r"[A-Z]{6}", sym.upper())
    if base:
        return base.group(0) + "c"
    else:
        # Nếu không match (trường hợp đặc biệt) thì fallback
        return sym.rstrip("cm") + "c"
