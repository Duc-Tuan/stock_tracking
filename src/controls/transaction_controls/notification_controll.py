from src.models.modelTransaction.setting_close_odd import SettingCloseOddTransaction
from src.models.modelTransaction.setting_close_odd_daily_risk import SettingCloseOddDailyRiskTransaction
from src.models.modelTransaction.notification_transansaction import NotificationTransaction
from src.models.model import SessionLocal
from datetime import datetime
from sqlalchemy import func
from src.models.modelTransaction.schemas import CloseFastLotRequest
from sqlalchemy.orm import joinedload

def post_setting_daily_risk_acc_transaction_controll(data):
    db = SessionLocal()
    try:
        isCheck = db.query(SettingCloseOddDailyRiskTransaction).filter(SettingCloseOddDailyRiskTransaction.risk == data.risk).all()
        if (len(isCheck) == 0):
            createNew = SettingCloseOddDailyRiskTransaction(
                loginId = 1,
                risk=data.risk
            )
            db.add(createNew)
            db.commit()
        else:
            return {"status": "error", "mess": "Đã tồn tại"}
        return {"status": "success", "mess": "Thêm mới thành công"}
    except Exception as e:
        db.rollback()
        print("Đã xảy ra lỗi khi tạo mới bảng setting_risk: ", e)
    finally:
        db.close()

def setting_daily_risk_acc_transaction_controll(data, id_user):
    db = SessionLocal()
    try:
        offset = (data['page'] - 1) * data['limit']

        query = db.query(SettingCloseOddDailyRiskTransaction)

        # Danh sách các điều kiện động
        filters = [SettingCloseOddDailyRiskTransaction.loginId == id_user]

        if data['start_time'] is not None:
            start_dt = datetime.fromtimestamp(int(data['start_time']) / 1000)
            filters.append(SettingCloseOddDailyRiskTransaction.time >= start_dt)

        if data['end_time'] is not None:
            end_dt = datetime.fromtimestamp(int(data['end_time']) / 1000)
            filters.append(SettingCloseOddDailyRiskTransaction.time <= end_dt)
            
        total = db.query(func.count(SettingCloseOddDailyRiskTransaction.id)).filter(*filters).scalar()

        dataOrdersClose = (
            query.filter(*filters)
            .order_by(SettingCloseOddDailyRiskTransaction.time.desc())
            .offset(offset)
            .limit(data['limit'])
            .all()
        )

        return {
            "total": total,
            "page": data['page'],
            "limit": data['limit'],
            "data": dataOrdersClose
        }
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def setting_risk_acc_transaction_controll(data):
    db = SessionLocal()
    try:
        isCheck = db.query(SettingCloseOddTransaction).filter(SettingCloseOddTransaction.risk == data.risk).all()
        if (len(isCheck) == 0):
            createNew = SettingCloseOddTransaction(
                loginId = 1,
                risk=data.risk
            )
            db.add(createNew)
            db.commit()
        else:
            return {"status": "error", "mess": "Đã tồn tại"}
        return {"status": "success", "mess": "Thêm mới thành công"}
    except Exception as e:
        db.rollback()
        print("Đã xảy ra lỗi khi tạo mới bảng setting_risk: ", e)
    finally:
        db.close()

def get_setting_risk_acc_transaction_controll(data, id_user):
    db = SessionLocal()
    try:
        offset = (data['page'] - 1) * data['limit']

        query = db.query(SettingCloseOddTransaction)

        # Danh sách các điều kiện động
        filters = [SettingCloseOddTransaction.loginId == id_user]

        if data['start_time'] is not None:
            start_dt = datetime.fromtimestamp(int(data['start_time']) / 1000)
            filters.append(SettingCloseOddTransaction.time >= start_dt)

        if data['end_time'] is not None:
            end_dt = datetime.fromtimestamp(int(data['end_time']) / 1000)
            filters.append(SettingCloseOddTransaction.time <= end_dt)
            
        total = db.query(func.count(SettingCloseOddTransaction.id)).filter(*filters).scalar()

        dataOrdersClose = (
            query.filter(*filters)
            .order_by(SettingCloseOddTransaction.time.desc())
            .offset(offset)
            .limit(data['limit'])
            .all()
        )

        return {
            "total": total,
            "page": data['page'],
            "limit": data['limit'],
            "data": dataOrdersClose
        }
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def get_notification_controll(data, id_user):
    db = SessionLocal()
    try:
        offset = (data['page'] - 1) * data['limit']

        query = db.query(NotificationTransaction)

        # Danh sách các điều kiện động
        filters = [NotificationTransaction.loginId == id_user]

        if data['start_time'] is not None:
            start_dt = datetime.fromtimestamp(int(data['start_time']) / 1000)
            filters.append(NotificationTransaction.time >= start_dt)

        if data['end_time'] is not None:
            end_dt = datetime.fromtimestamp(int(data['end_time']) / 1000)
            filters.append(NotificationTransaction.time <= end_dt)
            
        total = db.query(func.count(NotificationTransaction.id)).filter(*filters).scalar()

        total_notification = db.query(func.count(NotificationTransaction.id)).filter(NotificationTransaction.isRead == False).scalar()

        dataOrdersClose = (
            query.filter(*filters)
            .order_by(NotificationTransaction.time.desc())
            .offset(offset)
            .limit(data['limit'])
            .all()
        )

        return {
            "total": total,
            "page": data['page'],
            "limit": data['limit'],
            "data": dataOrdersClose,
            "total_notification": total_notification
        }
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def post_notification_read(data: CloseFastLotRequest, loginId: int):
    db = SessionLocal()
    try:
        if (len(data.data) == 0):
            db.query(NotificationTransaction).filter(NotificationTransaction.isRead == False).update({"isRead": True})
        else:
            for item in data.data:
                isCheck = db.query(NotificationTransaction).filter(NotificationTransaction.id == item.id, NotificationTransaction.isRead == False ).first()
                if (isCheck):
                    db.query(NotificationTransaction).filter(
                        NotificationTransaction.id == item.id,
                        NotificationTransaction.isRead == False
                    ).update({"isRead": True})
        db.commit()
        total_notification = db.query(func.count(NotificationTransaction.id)).filter(NotificationTransaction.isRead == False).scalar()
        return {"status": "success", "mess": "Update thành công", "total_notification": total_notification}
    except Exception as e:
        db.rollback()
        print("Đã xảy ra lỗi khi đổi trạng thái đã đọc trong notification: ", e)
    finally:
        db.close()

def get_detail_notification_read(id: int, loginId: int):
    db = SessionLocal()
    try:
        notif = db.query(NotificationTransaction).options(joinedload(NotificationTransaction.deals)).filter(NotificationTransaction.id == id).first()
        return notif   
    except Exception as e:
        db.rollback()
        print("Đã xảy ra lỗi khi đổi trạng thái đã đọc trong notification: ", e)
    finally:
        db.close()
