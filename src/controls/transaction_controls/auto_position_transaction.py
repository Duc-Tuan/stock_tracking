import time
import MetaTrader5 as mt5
from src.models.model import SessionLocal
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelTransaction.position_transaction_model import PositionTransaction
from concurrent.futures import ThreadPoolExecutor, as_completed

# Khởi tạo MT5 1 lần khi app start
def mt5_connect(path):
    if not mt5.initialize(path=path):
        raise Exception(f"MT5 chưa kết nối. Lỗi: {mt5.last_error()}")
    return True

def run_order(data: SymbolTransaction, mt5_path):
    mt5_connect(mt5_path)

    db = SessionLocal()
    position = mt5.positions_get(ticket=data.id_transaction)
    try:
        if position:
            pos = position[0]
            isPosition = db.query(PositionTransaction).filter(PositionTransaction.id_transaction == pos.ticket).order_by(PositionTransaction.time.desc()).first()
            if (isPosition):
                db.query(PositionTransaction).filter(PositionTransaction.id_transaction == pos.ticket).update({
                    "current_price": pos.price_current,
                    "swap": pos.swap,
                    "profit": pos.profit,
                    "open_price": pos.price_open
                })
            else:
                dataNew = PositionTransaction(
                    id_transaction = pos.ticket,
                    username_id = data.username_id,
                    account_id = data.account_transaction_id,
                    symbol = pos.symbol,
                    position_type = data.type,
                    volume = pos.volume,
                    open_price = pos.price_open,
                    current_price = pos.price_current,
                    sl = pos.sl,
                    tp = pos.tp,
                    # open_time = pos.time,
                    magic_number = 123456,
                    comment = pos.comment,
                    swap = pos.swap,
                    profit = pos.profit
                )
                db.add(dataNew)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi trong auto_position: {e}")
    finally:
        db.close()

def auto_position(mt5_path, account_name, interval, stop_event):
    try: 
        while not stop_event.is_set():
            db = SessionLocal()
            try:
                dataOrder = db.query(SymbolTransaction).filter(SymbolTransaction.status == "filled").order_by(SymbolTransaction.time.desc()).all()

                results = []
                with ThreadPoolExecutor() as executor:
                    futures = [executor.submit(run_order, order, mt5_path) for order in dataOrder]
                    for future in as_completed(futures):
                        results.append(future.result())
                print("✅ theo dõi tick đã vào lệnh trên MT5")
            except Exception as e:
                db.rollback()
                print(f"[{account_name}] ❌ Lỗi trong monitor_account: {e}")
            finally:
                db.close()
                time.sleep(interval)
    except KeyboardInterrupt:
        print("🔝 Logger process interrupted with Ctrl+C. Exiting gracefully.")
    finally:
        mt5.shutdown()