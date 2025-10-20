from src.models.model import SessionLocal
from src.models.modelBoot.info_lo_transaction_model import InfoLoTransactionBoot

def get_unique_pairs(data):
    return list({tuple(sorted([d['acc_reciprocal'], d['acc_reference']])) for d in data})

def account_filtering():
    try: 
        db = SessionLocal()
        data = db.query(InfoLoTransactionBoot).filter(InfoLoTransactionBoot.type == "RUNNING").all()

        result = []
        for row in data:
            row_dict = row.__dict__.copy()
            row_dict.pop("_sa_instance_state", None)
            result.append(row_dict)

        unique_accounts = list({x for d in result for x in (d['acc_reciprocal'], d['acc_reference'])})

        return unique_accounts
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi trong vào lệnh: {e}") 
    finally:
        db.close()