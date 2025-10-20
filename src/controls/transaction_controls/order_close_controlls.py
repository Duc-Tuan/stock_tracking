from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.model import SessionLocal
from sqlalchemy import func, case
from datetime import datetime

def get_order_close(data, id_user):
    db = SessionLocal()
    try:
        offset = (data['page'] - 1) * data['limit']

        query = db.query(SymbolTransaction)

        start_dt = None
        end_dt = None

        # Danh sách các điều kiện động
        filters = [SymbolTransaction.username_id == id_user, SymbolTransaction.status == "cancelled"]

        if data['acc_transaction'] is not None:
            filters.append(SymbolTransaction.account_transaction_id == int(data['acc_transaction']))

        if data['symbol'] is not None:
            filters.append(SymbolTransaction.symbol == data['symbol'])

        if data['start_time'] is not None:
            start_dt = datetime.fromtimestamp(int(data['start_time']) / 1000)
            filters.append(SymbolTransaction.time >= start_dt)

        if data['end_time'] is not None:
            end_dt = datetime.fromtimestamp(int(data['end_time']) / 1000)
            filters.append(SymbolTransaction.time <= end_dt)
            
        dataOrdersClose = (
            query.filter(*filters)
            .order_by(SymbolTransaction.time.desc())
            .offset(offset)
            .limit(data['limit'])
            .all()
        )

        total_all = db.query(func.count(SymbolTransaction.id)).filter(SymbolTransaction.status == "cancelled").scalar()

        result = db.query(
            func.count(SymbolTransaction.id).label("total_filtered"),
            func.sum(case((SymbolTransaction.type.in_(["BUY", "SELL"]), 1), else_=0)).label("total_both_filtered"),
        ).filter(*filters).first()

        today = datetime.now().date()
        if start_dt is None or end_dt is None:
            start_dt = datetime.combine(today, datetime.min.time())   # 00:00:00 hôm nay
            end_dt   = datetime.combine(today, datetime.max.time())   # 23:59:59 hôm nay

        results = (
            db.query(
                SymbolTransaction.account_transaction_id,
                func.sum(SymbolTransaction.profit).label("total_profit"),
                func.count(SymbolTransaction.id).label("transaction_count")
            )
            .filter(
                SymbolTransaction.username_id == id_user, 
                SymbolTransaction.status == "cancelled",
                SymbolTransaction.time >= start_dt,
                SymbolTransaction.time <= end_dt
            )
            .group_by(SymbolTransaction.account_transaction_id)
            .all()
        )

        results_dict = [
            {
                "account_transaction_id": account_id,
                "total_profit": total_profit,
                "transaction_count": transaction_count,
                "time": today.isoformat()
            }
            for account_id, total_profit, transaction_count in results
        ]

        return {
            "totalOrder": total_all,
            "total": result.total_filtered or 0,
            "page": data['page'],
            "limit": data['limit'],
            "data": dataOrdersClose,
            "profit": results_dict
        }
    except Exception as e:
        db.rollback()
    finally:
        db.close()