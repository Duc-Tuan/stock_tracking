from src.models.modelTransaction.deal_transaction_model import DealTransaction
from src.models.model import SessionLocal
from sqlalchemy import func
from datetime import datetime

def get_order_close(data, id_user):
    db = SessionLocal()
    try:
        offset = (data['page'] - 1) * data['limit']

        query = db.query(DealTransaction)

        # Danh sách các điều kiện động
        filters = [DealTransaction.username_id == id_user]

        if data['acc_transaction'] is not None:
            filters.append(DealTransaction.account_id == int(data['acc_transaction']))

        if data['symbol'] is not None:
            filters.append(DealTransaction.symbol == data['symbol'])

        if data['start_time'] is not None:
            start_dt = datetime.fromtimestamp(int(data['start_time']) / 1000)
            filters.append(DealTransaction.close_time >= start_dt)

        if data['end_time'] is not None:
            end_dt = datetime.fromtimestamp(int(data['end_time']) / 1000)
            filters.append(DealTransaction.close_time <= end_dt)
            
        total = db.query(func.count(DealTransaction.id)).filter(*filters).scalar()

        dataOrdersClose = (
            query.filter(*filters)
            .order_by(DealTransaction.close_time.desc())
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