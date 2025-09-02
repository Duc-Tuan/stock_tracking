from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from src.middlewares.authMiddleware import pwd_context
from src.utils.options import RegisterRequest, RegisterRequestAccMt5
from src.middlewares.authMiddleware import hash_password, encrypt_password_mt5
from src.models.modelsUser import UserModel
from src.models.modelAccMt5 import AccountMt5
from src.models.model import SessionLocal
from src.utils.options import SECRET_KEY, ALGORITHM

# Token

# Dependency dùng cho bảo vệ route
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    try:
        data = db.query(UserModel).filter(UserModel.username == username).first()
        return data
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_user(payload: RegisterRequest, db):
    try:
        hashed_pw = hash_password(payload.password)
        new_user = UserModel(username=payload.username, hashed_password=hashed_pw, role="viewer")
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return new_user
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Không thể xác thực token",
        headers={"Authorization": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.username == username).first()
        db.close()
        if not user:
            raise credentials_exception
        return user  # user có user.role
    except Exception as e:
        db.rollback()
    finally:
        db.close()


def def_create_acc_mt5(payload: RegisterRequestAccMt5, loginId, db):
    try: 
        hashed_pw = encrypt_password_mt5(payload.password)
        new_data = AccountMt5(username=payload.username, password=hashed_pw, loginId=loginId, server=payload.server)
        db.add(new_data)
        db.commit()
        db.refresh(new_data)
        return new_data
    except Exception as e:
        db.rollback()
    finally:
        db.close()