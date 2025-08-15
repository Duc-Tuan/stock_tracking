from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.model import SessionLocal
from sqlalchemy import func
from datetime import datetime

def get_all_send_symbols(data, id_user):
    db = SessionLocal()
    try:
        offset = (data['page'] - 1) * data['limit']

        query = db.query(SymbolTransaction)

        # Danh sách các điều kiện động
        filters = [SymbolTransaction.username_id == id_user]

        if data['acc_transaction'] is not None:
            filters.append(SymbolTransaction.account_transaction_id == int(data['acc_transaction']))

        if data['symbol'] is not None:
            filters.append(SymbolTransaction.symbol == data['symbol'])

        if data['status'] is not None:
            filters.append(SymbolTransaction.status == data['status'])

        if data['type'] is not None:
            filters.append(SymbolTransaction.type == data['type'])

        if data['start_time'] is not None:
            start_dt = datetime.fromtimestamp(int(data['start_time']) / 1000)
            filters.append(SymbolTransaction.time >= start_dt)

        if data['end_time'] is not None:
            end_dt = datetime.fromtimestamp(int(data['end_time']) / 1000)
            filters.append(SymbolTransaction.time <= end_dt)
            
        total = db.query(func.count(SymbolTransaction.id)).filter(*filters).scalar()

        dataOrdersClose = (
            query.filter(*filters)
            .order_by(SymbolTransaction.time.desc())
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