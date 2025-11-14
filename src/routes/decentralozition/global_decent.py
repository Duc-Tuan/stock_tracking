from fastapi import APIRouter, Depends, HTTPException, Request
from src.models.modelsUser import UserModel

def checkDataEmty(db, data):
    user = db.query(UserModel).filter(UserModel.id == data.user_id).first()

    if (user.role.value == "admin"):
        raise HTTPException(status_code=404, detail="Không thể phân quyền cho tài khoản admin")

    return user

def checkAdminDataEmty(db, id):
    user = db.query(UserModel).filter(UserModel.id == id).first()

    if (user.role.value != "admin"):
        raise HTTPException(status_code=404, detail="Bạn không có quyền thực hiện chức năng này")

    return user