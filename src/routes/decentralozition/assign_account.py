from fastapi import APIRouter, Depends, HTTPException, Request
from src.models.modelAccMt5 import AccountMt5
from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction
from src.controls.authControll import get_current_admin
from src.middlewares.authMiddleware import get_db
from sqlalchemy.orm import Session
from src.models.modelsUser import UserModel
from src.models.model import SessionLocal
from src.models.modelTransaction.schemas import AssignAccountRequest, CloseFastLotItem
from src.models.modelDecentralization.modelUser import user_mt5_association, user_acc_transaction_association
from src.routes.decentralozition.global_decent import checkDataEmty, checkAdminDataEmty

router = APIRouter()

@router.post("/assign_account")
def assign_account_to_user(data: AssignAccountRequest,
    current_admin: UserModel = Depends(get_current_admin),
    db: Session = Depends(get_db)):
    account = db.query(AccountMt5).filter(AccountMt5.id == data.account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="User hoặc Account không tồn tại")
    user = checkDataEmty(db, data)

    exists = db.query(user_mt5_association).filter(
        user_mt5_association.c.user_id == user.id,
        user_mt5_association.c.account_mt5_id == account.id
    ).first()

    if (exists):
        raise HTTPException(status_code=404, detail=f"User {user.username} đã có quyền xem loginId = {account.loginId} rồi")
    
    try:
        user.accounts.append(account)
        db.commit()
        db.refresh(user)

        dataCheckId = db.query(user_mt5_association).filter(
            user_mt5_association.c.user_id == user.id,
            user_mt5_association.c.account_mt5_id == account.id
        ).first()

        return {"msg": f"Đã cấp quyền xem server theo dõi: {account.username} cho user {user.username}", "id": dataCheckId.id}
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)

@router.delete("/assign_account")
def assign_account_to_user(data: CloseFastLotItem,
    current_admin: UserModel = Depends(get_current_admin),
    db: Session = Depends(get_db)):
    user = checkAdminDataEmty(db, current_admin.id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user.username} Không có quyền thay đổi chức năng phân quyền")
    try:
        db.query(user_mt5_association).filter(
            user_mt5_association.c.id == data.id
        ).delete()

        db.commit()
        return {"msg": f"Đã xóa thành công phân quyền xem cho user {user.username}"}
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)


@router.post("/assign_account_transaction")
def assign_account_to_user(data: AssignAccountRequest,
    current_admin: UserModel = Depends(get_current_admin),
    db: Session = Depends(get_db)):
    account = db.query(AccountsTransaction).filter(AccountsTransaction.id == data.account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="User hoặc Account không tồn tại")
    
    user = checkDataEmty(db, data)

    exists = db.query(user_acc_transaction_association).filter(
        user_acc_transaction_association.c.user_id == user.id,
        user_acc_transaction_association.c.acc_transaction_id == account.id
    ).first()

    if (exists):
        raise HTTPException(status_code=404, detail=f"User {user.username} đã có quyền xem TKGD: {account.username} rồi")

    try:
        user.accountsTransaction.append(account)
        db.commit()
        db.refresh(user)

        dataCheckId = db.query(user_acc_transaction_association).filter(
            user_acc_transaction_association.c.user_id == user.id,
            user_acc_transaction_association.c.acc_transaction_id == account.id
        ).first()

        return {"msg": f"Đã cấp quyền xem TKGD: {account.username} cho user {user.username}", "id": dataCheckId.id}
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)
    
@router.delete("/assign_account_transaction")
def assign_account_to_user(data: CloseFastLotItem,
    current_admin: UserModel = Depends(get_current_admin),
    db: Session = Depends(get_db)):
    try:
        user = checkAdminDataEmty(db, current_admin.id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user.username} Không có quyền thay đổi chức năng phân quyền")

        db.query(user_acc_transaction_association).filter(
            user_acc_transaction_association.c.id == data.id
        ).delete()

        db.commit()
        return {"msg": f"Đã xóa thành công phân quyền xem cho user {user.username}"}
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)