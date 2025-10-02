from fastapi import APIRouter, Depends, HTTPException
from src.middlewares.authMiddleware import get_db
from sqlalchemy.orm import Session
from src.controls.authControll import get_current_user
from src.utils.options import RegisterRequestAccMt5, UpdateRiskAccTransaction
from src.controls.accmt5Controll import create_acc_mt5_controll
from src.controls.accmt5Controll import get_acc_mt5_controll, get_acc_mt5_transaction, get_swaps_controll, update_risk_acc_mt5_transaction

router = APIRouter()

@router.get("/accmt5")
def login_acc_mt5(current_user: dict =Depends(get_current_user), db: Session = Depends(get_db)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền thêm tài khoản mt5")
    data = get_acc_mt5_controll(db, current_user.username)
    return {"data": data, "status": 200 }

@router.get("/swaps")
def login_acc_mt5(current_user: dict =Depends(get_current_user), db: Session = Depends(get_db)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem swap")
    data = get_swaps_controll(db, current_user.username)
    return {"data": data, "status": 200 }

@router.get("/accmt5_transaction")
def login_acc_mt5(current_user: dict =Depends(get_current_user), db: Session = Depends(get_db)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền thêm tài khoản mt5")
    data = get_acc_mt5_transaction(db, current_user.username)
    return {"data": data, "status": 200 }

@router.post("/accmt5_transaction")
def login_acc_mt5(data: UpdateRiskAccTransaction,current_user: dict =Depends(get_current_user), db: Session = Depends(get_db)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền thêm tài khoản mt5")
    return update_risk_acc_mt5_transaction(db, data, current_user.id)

@router.post("/accmt5")
def create_acc_mt5(payload: RegisterRequestAccMt5,current_user: dict =Depends(get_current_user), db: Session = Depends(get_db)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền thêm tài khoản mt5")

    return create_acc_mt5_controll(payload, db, current_user)
    