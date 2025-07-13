from fastapi import APIRouter, Depends, HTTPException
from src.models.modelAccMt5 import AccountMt5
from src.utils.options import RegisterRequestAccMt5
import MetaTrader5 as mt5
from src.controls.authControll import def_create_acc_mt5, get_user
from jose import JWTError
from fastapi.encoders import jsonable_encoder


def create_acc_mt5_controll(payload: RegisterRequestAccMt5,db, current_user):
    # Kiểm tra username tồn tại
    existing = db.query(AccountMt5).filter(
        AccountMt5.username == payload.username,
        AccountMt5.server == payload.server).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tài khoản đã tồn tại")
   
    if not mt5.initialize(login=payload.username, password=payload.password, server=payload.server):
        print(f"❌ Login thất bại: {payload.username}")
        raise HTTPException(status_code=400, detail="Đăng nhập tài khoản thất bại." )
    mt5.shutdown()

    try:
        dataAccMt5 = def_create_acc_mt5(payload, current_user.id, db)
        return {"message": f"Đăng ký thành công cho user: {dataAccMt5.username}"}
    except JWTError:
        raise HTTPException(status_code=400, detail="Đăng nhập thất bại")

def get_acc_mt5_controll(db, username: str):
    user = get_user(db, username)
    if not user:
        return False
    existing = db.query(AccountMt5).filter(AccountMt5.loginId == user.id).all()

    result = []
    for row in existing:
        row_dict = row.__dict__.copy()
        row_dict.pop("_sa_instance_state", None)
        row_dict.pop("password", None)  # bỏ trường login nếu cần
        row_dict.pop("loginId", None)  # bỏ trường login nếu cần
        result.append(row_dict)

    return result