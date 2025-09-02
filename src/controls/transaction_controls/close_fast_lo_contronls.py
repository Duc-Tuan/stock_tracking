from concurrent.futures import ThreadPoolExecutor, as_completed

from src.models.model import SessionLocal
from src.models.modelTransaction.schemas import CloseFastLotRequest
from src.models.modelTransaction.lot_information_model import LotInformation

from src.controls.transaction_controls.auto_order import run_order_close

def run_lots(id_lot: int, id_user: int):
    db = SessionLocal()
    try:
        dataLots = db.query(LotInformation).filter(LotInformation.id == id_lot, LotInformation.username_id == id_user, LotInformation.status == "Lenh_thi_truong").order_by(LotInformation.time.desc()).all()
        results = []
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(run_order_close, dataLot) for dataLot in dataLots]
            for future in as_completed(futures):
                results.append(future.result())
        return results
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi trong đóng lệnh nhanh: {e}")
    finally:
        db.close()


def close_fast_lot_contronlls(datas: CloseFastLotRequest, current_user_id: int):
    results = []
    print(datas)
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_lots, data.id, current_user_id) for data in datas]
        for future in as_completed(futures):
            results.append(future.result())
    return results