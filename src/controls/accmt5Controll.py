from fastapi import APIRouter, Depends, HTTPException
from src.models.modelAccMt5 import AccountMt5
from src.models.modelSwapMt5 import SwapMt5
from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction
from src.models.modelTransaction.setting_close_odd import SettingCloseOddTransaction
from src.models.modelTransaction.setting_close_odd_daily_risk import SettingCloseOddDailyRiskTransaction
from src.utils.options import RegisterRequestAccMt5
import MetaTrader5 as mt5
from src.controls.authControll import def_create_acc_mt5, get_user
from jose import JWTError
from sqlalchemy import desc
from src.models.modelDecentralization.modelUser import user_mt5_association, user_acc_transaction_association
from src.models.modelsUser import UserModel

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
    try:
        user = get_user(db, username)
        if not user:
            return False

        # Truy vấn username của tất cả user liên kết với các account này
        usernames = db.query(user_mt5_association).filter(
            user_mt5_association.c.user_id == user.id
        ).all()
        
        usernames_list = [u[2] for u in usernames]

        existing = db.query(AccountMt5).filter(AccountMt5.loginId == user.id).all()
        if (user.role.value != "admin"):
            existing = db.query(AccountMt5).filter(AccountMt5.id.in_(usernames_list)).all()

        result = []
        for row in existing:
            row_dict = row.__dict__.copy()
            row_dict.pop("_sa_instance_state", None)
            row_dict.pop("password", None)  # bỏ trường login nếu cần
            row_dict.pop("loginId", None)  # bỏ trường login nếu cần
            result.append(row_dict)

        return result
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def get_swaps_controll(db, username: str):
    try:
        user = get_user(db, username)
        if not user:
            return False
        # Lấy 10 bản ghi mới nhất theo id (hoặc created_at)
        existing = (
            db.query(SwapMt5)
            .order_by(desc(SwapMt5.id))   # hoặc SwapMt5.created_at nếu có
            .limit(10)
            .all()
        )

        result = []
        for row in existing:
            row_dict = row.__dict__.copy()
            row_dict.pop("_sa_instance_state", None)
            row_dict.pop("password", None)
            row_dict.pop("loginId", None)
            result.append(row_dict)

        return result
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

from sqlalchemy.inspection import inspect

def to_dict(obj):
    """Chỉ lấy dữ liệu các cột trong bảng, bỏ qua state"""
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}

def get_acc_mt5_transaction(db, username: str):
    try:
        user = get_user(db, username)
        if not user:
            return False

        usernames = db.query(user_acc_transaction_association).filter(
            user_acc_transaction_association.c.user_id == user.id
        ).all()
        
        usernames_list = [u[2] for u in usernames]

        query = (
            db.query(AccountsTransaction, SettingCloseOddTransaction, SettingCloseOddDailyRiskTransaction)
            .outerjoin(
                SettingCloseOddTransaction,
                AccountsTransaction.id_setting_close_odd == SettingCloseOddTransaction.id
            )
            .outerjoin(
                SettingCloseOddDailyRiskTransaction,
                AccountsTransaction.id_setting_close_odd_daily_risk == SettingCloseOddDailyRiskTransaction.id
            )
            .filter(AccountsTransaction.loginId == user.id)
        )
        if (user.role.value != "admin"):
            existing = db.query(AccountMt5).filter(AccountMt5.id.in_(usernames_list)).all()
            # existing = db.query(AccountsTransaction).filter(AccountsTransaction.loginId == user.id).all()
            query = (
                db.query(AccountsTransaction, SettingCloseOddTransaction, SettingCloseOddDailyRiskTransaction)
                .outerjoin(
                    SettingCloseOddTransaction,
                    AccountsTransaction.id_setting_close_odd == SettingCloseOddTransaction.id
                )
                .outerjoin(
                    SettingCloseOddDailyRiskTransaction,
                    AccountsTransaction.id_setting_close_odd_daily_risk == SettingCloseOddDailyRiskTransaction.id
                )
                .filter(AccountsTransaction.id.in_(usernames_list))
            )

        rows = query.all()


        # Trả ra list dict, gộp cả 2 bảng
        result = []
        for acc, setting, daily in rows:
            acc_dict = to_dict(acc)

            # Risk từ SettingCloseOddTransaction
            acc_dict["risk"] = setting.risk if setting else None

            # Risk từ SettingCloseOddDailyRiskTransaction
            acc_dict["daily_risk"] = daily.risk if daily else None

            result.append(acc_dict)

        return result

    except Exception as e:
        db.rollback()
    finally:
        db.close()

def get_acc_mt5_setting_daily_risk_transaction(db, username: str):
    try:
        user = get_user(db, username)
        if not user:
            return False

        # existing = db.query(AccountsTransaction).filter(AccountsTransaction.loginId == user.id).all()
        query = (
            db.query(AccountsTransaction, SettingCloseOddDailyRiskTransaction)
            .outerjoin(
                SettingCloseOddDailyRiskTransaction,
                AccountsTransaction.id_setting_close_odd_daily_risk == SettingCloseOddDailyRiskTransaction.id
            )
            .filter(AccountsTransaction.loginId == user.id)
        )

        rows = query.all()

        # Trả ra list dict, gộp cả 2 bảng
        result = []
        for acc, setting in rows:
            acc_dict = to_dict(acc)
            if setting:
                acc_dict["risk"] = setting.risk
            else:
                acc_dict["risk"] = None
            result.append(acc_dict)

        return result

    except Exception as e:
        db.rollback()
    finally:
        db.close()

def update_risk_acc_mt5_transaction(db, data, username: str):
    try:
        existing = db.query(AccountsTransaction).filter(
            AccountsTransaction.id == data.id_acc,
            AccountsTransaction.loginId == username
        ).first()

        if not existing:
            raise HTTPException(status_code=404, detail="Tài khoản không tồn tại")

        # chỉ update những field nào có giá trị
        if data.id_Risk is not None:
            existing.id_setting_close_odd = data.id_Risk
        if data.id_daily_risk is not None:
            existing.id_setting_close_odd_daily_risk = data.id_daily_risk
        if data.monney_acc is not None:
            existing.monney_acc = data.monney_acc
        if data.type_acc is not None:
            existing.type_acc = data.type_acc

        db.commit()
        db.refresh(existing)
        return existing

    except HTTPException:  # giữ nguyên HTTPException, không rollback ở đây
        raise
    except Exception as e:
        db.rollback()
        raise e   # re-raise để FastAPI xử lý thành 500
    finally:
        db.close()