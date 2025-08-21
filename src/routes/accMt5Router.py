from fastapi import APIRouter, Depends, HTTPException
from src.middlewares.authMiddleware import get_db
from sqlalchemy.orm import Session
from src.controls.authControll import get_current_user
from src.utils.options import RegisterRequestAccMt5
from src.controls.accmt5Controll import create_acc_mt5_controll
from src.controls.accmt5Controll import get_acc_mt5_controll, get_acc_mt5_transaction

router = APIRouter()

@router.get("/accmt5")
def login_acc_mt5(current_user: dict =Depends(get_current_user), db: Session = Depends(get_db)):
    data = get_acc_mt5_controll(db, current_user.username)
    if not data:
        raise HTTPException(status_code=401, detail="Sai username hoặc password")
    return {"data": data, "status": 200 }

@router.get("/accmt5_transaction")
def login_acc_mt5(current_user: dict =Depends(get_current_user), db: Session = Depends(get_db)):
    data = get_acc_mt5_transaction(db, current_user.username)
    if not data:
        raise HTTPException(status_code=401, detail="Sai username hoặc password")
    return {"data": data, "status": 200 }

@router.post("/accmt5")
def create_acc_mt5(payload: RegisterRequestAccMt5,current_user: dict =Depends(get_current_user), db: Session = Depends(get_db)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền thêm tài khoản mt5")

    return create_acc_mt5_controll(payload, db, current_user)
    