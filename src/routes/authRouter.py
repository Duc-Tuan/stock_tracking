from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from src.controls.authControll import authenticate_user, create_access_token, get_current_user
from datetime import timedelta
from sqlalchemy.orm import Session
from src.models.modelsUser import UserModel
from src.middlewares.authMiddleware import get_db
from pydantic import BaseModel
from src.controls.authControll import create_user
from src.utils.options import RegisterRequest

router = APIRouter()

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Sai username hoặc password")

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=(60 * 24))
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register")
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    # Kiểm tra username tồn tại
    existing = db.query(UserModel).filter(UserModel.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username đã tồn tại")
    
    new_user = create_user(payload, db)
    return {"message": f"Đăng ký thành công cho user: {new_user.username}"}

# ✅ Route được bảo vệ
@router.get("/me")
def read_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username
    }
