import time
import MetaTrader5 as mt5
from src.models.model import SessionLocal
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelTransaction.position_transaction_model import PositionTransaction
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.services.terminals_transaction import terminals_transaction
from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction
from src.services.socket_manager import emit_sync
import random

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
    result = None
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
                result = dict(
                    id_transaction=isPosition.id_transaction,
                    username_id=isPosition.username_id,
                    account_id=isPosition.account_id,
                    symbol=isPosition.symbol,
                    position_type=isPosition.position_type,
                    volume=isPosition.volume,
                    open_price=pos.price_open,
                    current_price=pos.price_current,
                    sl=isPosition.sl,
                    tp=isPosition.tp,
                    magic_number=isPosition.magic_number,
                    comment=isPosition.comment,
                    swap=pos.swap,
                    profit=pos.profit
                )
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
                    magic_number = 123456,
                    comment = pos.comment,
                    swap = pos.swap,
                    profit = pos.profit
                )
                db.add(dataNew)
                result = dict(
                    id_transaction=dataNew.id_transaction,
                    username_id=dataNew.username_id,
                    account_id=dataNew.account_id,
                    symbol=dataNew.symbol,
                    position_type=dataNew.position_type,
                    volume=dataNew.volume,
                    open_price=dataNew.open_price,
                    current_price=dataNew.current_price,
                    sl=dataNew.sl,
                    tp=dataNew.tp,
                    magic_number=dataNew.magic_number,
                    comment=dataNew.comment,
                    swap=dataNew.swap,
                    profit=dataNew.profit
                )
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi trong auto_position: {e}")
    finally:
        db.close()
        return result

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
                        if future.result():  # chỉ thêm nếu có dữ liệu
                            results.append(future.result())

                # Lấy dữ liệu trước khi đóng session
                acc_data = [dict(
                    id=a.id,
                    username=a.username,
                    server=a.server,
                    balance=a.balance,
                    equity=a.equity,
                    margin=a.margin,
                    free_margin=a.free_margin,
                    leverage=a.leverage,
                    name=a.name,
                    loginId=a.loginId,
                ) for a in db.query(AccountsTransaction).all()]

                emit_sync("position_message", {"acc": acc_data, "positions": results})

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