from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from src.controls.authControll import authenticate_user, create_access_token, get_current_user
from datetime import timedelta
from sqlalchemy.orm import Session
from src.models.modelsUser import UserModel
from src.middlewares.authMiddleware import get_db
from src.models.modelNote import Note
from src.controls.authControll import create_user
from src.utils.options import RegisterRequest
from src.controls.authControll import get_current_admin
from src.models.modelTransaction.schemas import CloseFastLotItem
from src.models.modelDecentralization.modelUser import user_mt5_association, user_acc_transaction_association

router = APIRouter()

@router.post("/login")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    form = await request.form()
    device_id = form.get("deviceId")  # 👈 Lấy device_id thủ công

    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Sai username hoặc password")
    
    # # Kiểm tra thiết bị đã tồn tại chưa
    # existing_token = db.query(UserToken).filter(
    #     UserToken.user_id == user.id,
    #     UserToken.device_id == device_id
    # ).first()

    # if existing_token:
    #     # Nếu đã có thiết bị này, xóa token cũ (nó có thể đã mất ở client)
    #     db.delete(existing_token)
    #     db.commit()

    # # Kiểm tra số thiết bị còn lại (sau khi loại device hiện tại nếu có)
    # active_tokens = db.query(UserToken).filter(UserToken.user_id == user.id).all()

    # if len(active_tokens) >= 2:
    #     raise HTTPException(status_code=403, detail="Chỉ được đăng nhập trên tối đa 2 thiết bị.")

    # Tạo access token mới
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=(60 * 24))
    )

    # Lưu vào DB
    # db_token = UserToken(user_id=user.id, token=access_token, device_id=device_id)
    # db.add(db_token)
    # db.commit()

    return {"access_token": access_token, "token_type": "bearer", "deviceId": device_id}

@router.post("/register")
def register_user(payload: RegisterRequest, current_admin: UserModel = Depends(get_current_admin), db: Session = Depends(get_db)):
    # Kiểm tra username tồn tại
    existing = db.query(UserModel).filter(UserModel.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username đã tồn tại")
    
    new_user = create_user(payload, db)
    return {"message": f"Đăng ký thành công cho user: {new_user.username}", "id": new_user.id}

@router.delete("/user")
def register_user(data: CloseFastLotItem, current_admin: UserModel = Depends(get_current_admin), db: Session = Depends(get_db)):
    # Kiểm tra username tồn tại
    existing = db.query(UserModel).filter(UserModel.id == data.id).first()

    if not existing:
        raise HTTPException(status_code=400, detail="Username không tồn tại tồn tại")
    
    db.query(user_mt5_association).filter(
            user_mt5_association.c.user_id == existing.id
        ).delete()
    
    db.query(user_acc_transaction_association).filter(
            user_acc_transaction_association.c.user_id == existing.id
        ).delete()
    
    db.query(Note).filter(Note.login == existing.id).delete()

    db.query(UserModel).filter(UserModel.id == existing.id).delete()
    db.commit()

    return {"message": f"Đăng ký thành công cho user: {existing.username}"}

# ✅ Route được bảo vệ
@router.get("/me")
def read_me(current_user: dict = Depends(get_current_user)):
    role = 404
    if (str(current_user.role) == "UserRole.admin"):
        role = 200
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": role
    }
