import time
import MetaTrader5 as mt5
from src.models.model import SessionLocal
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelTransaction.position_transaction_model import PositionTransaction
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.services.terminals_transaction import terminals_transaction
from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction

# Khởi tạo MT5 1 lần khi app start
def mt5_connect(account_name: int):
    acc = terminals_transaction[str(account_name)]
    # Đóng kết nối cũ nếu đang mở
    mt5.shutdown()
    # Kết nối mới
    if not mt5.initialize(path=acc["path"]):
        raise Exception(f"Không connect được MT5 {account_name}. Lỗi: {mt5.last_error()}")
    return True

def run_order(data: SymbolTransaction):
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

def auto_position(account_name, interval, stop_event):
    try: 
        while not stop_event.is_set():
            mt5_connect(account_name)

            db = SessionLocal()
            try:
                dataOrder = db.query(SymbolTransaction).filter(SymbolTransaction.status == "filled").order_by(SymbolTransaction.time.desc()).all()

                account_info = mt5.account_info()

                existing = db.query(AccountsTransaction).filter(AccountsTransaction.username == int(account_info.login)).all()
                new_data = AccountsTransaction(
                    username=account_info.login,
                    server=account_info.server,
                    balance=account_info.balance,
                    equity=account_info.equity,
                    margin=account_info.margin,
                    free_margin=account_info.margin_free,
                    leverage=account_info.leverage,
                    name=account_info.login,
                    loginId=1
                )
                
                if (len(existing) == 0):
                    db.add(new_data)
                else:
                    db.query(AccountsTransaction).filter(AccountsTransaction.username == account_info.login).update({
                        "balance": account_info.balance,
                        "equity": account_info.equity,
                        "margin": account_info.margin,
                        "free_margin": account_info.margin_free,
                        "leverage": account_info.leverage,
                        "server": account_info.server,
                    })

                db.commit()
    
                results = []
                with ThreadPoolExecutor() as executor:
                    futures = [executor.submit(run_order, order) for order in dataOrder]
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