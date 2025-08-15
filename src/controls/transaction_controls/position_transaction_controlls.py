from src.models.modelTransaction.position_transaction_model import PositionTransaction
from src.models.model import SessionLocal
from sqlalchemy import func
from datetime import datetime

def position_transaction(data, id_user):
    db = SessionLocal()
    try:
        offset = (data['page'] - 1) * data['limit']

        query = db.query(PositionTransaction)

        # Danh sách các điều kiện động
        filters = [PositionTransaction.username_id == id_user]

        if data['acc_transaction'] is not None:
            filters.append(PositionTransaction.account_id == int(data['acc_transaction']))

        if data['symbol'] is not None:
            filters.append(PositionTransaction.symbol == data['symbol'])

        if data['type'] is not None:
            filters.append(PositionTransaction.position_type == data['type'])

        if data['start_time'] is not None:
            start_dt = datetime.fromtimestamp(int(data['start_time']) / 1000)
            filters.append(PositionTransaction.time >= start_dt)

        if data['end_time'] is not None:
            end_dt = datetime.fromtimestamp(int(data['end_time']) / 1000)
            filters.append(PositionTransaction.time <= end_dt)
            
        total = db.query(func.count(PositionTransaction.id)).filter(*filters).scalar()

        dataOrdersClose = (
            query.filter(*filters)
            .order_by(PositionTransaction.time.desc())
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