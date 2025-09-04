import re
import MetaTrader5 as mt5
import queue as pyqueue
from src.services.terminals_transaction import terminals_transaction
from src.services.socket_manager import emit_boot_opposition_sync
from src.models.model import SessionLocal
from src.models.modelBoot.accounts_transaction_model import AccountsBoot
from src.models.modelBoot.position_transaction_model import PositionBoot
from src.services.socket_manager import emit_sync

# Khởi tạo MT5 1 lần khi app start
def mt5_connect(account_name: int):
    acc = terminals_transaction[str(account_name)]
    # Đóng kết nối cũ nếu đang mở
    mt5.shutdown()
    # Kết nối mới
    if not mt5.initialize(path=acc['path']):
        raise Exception(f"Không connect được MT5 {account_name}. Lỗi: {mt5.last_error()}")
    return True

def boot_auto_opposition(name, cfg, queue, stop_event, pub_queue):
    mt5_connect(name)
    try: 
        while not stop_event.is_set():
            db = SessionLocal()
            try:
                item = queue.get(timeout=1)
            except pyqueue.Empty:
                # không có gì trong queue -> tiếp tục vòng lặp
                pass

            positions = mt5.positions_get()

            if positions:
                for pos in positions:
                    existing = db.query(PositionBoot).filter(PositionBoot.id_transaction == int(pos.ticket)).all()

                    new_data = PositionBoot(
                        id_transaction = pos.ticket,
                        username = int(name),
                        position_type = pos.type,
                        symbol = pos.symbol,
                        volume = pos.volume,
                        open_price = pos.price_open,
                        current_price =  pos.price_current,
                        sl = pos.sl,
                        tp = pos.tp,
                        swap = pos.swap,
                        profit = pos.profit,
                        commission = pos.profit,
                        magic_number = pos.magic,
                        comment = pos.comment
                    )

                    if (len(existing) == 0):
                        db.add(new_data)
                    else:
                        db.query(PositionBoot).filter(PositionBoot.id_transaction == int(pos.ticket)).update({
                            "open_price": pos.price_open,
                            "current_price":  pos.price_current,
                            "sl": pos.sl,
                            "tp": pos.tp,
                            "swap": pos.swap,
                            "profit": pos.profit,
                        })
                    db.commit()

            try:
                account_info = mt5.account_info()

                if (account_info):

                    existing = db.query(AccountsBoot).filter(AccountsBoot.username == int(account_info.login)).all()
                    new_data = AccountsBoot(
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
                        db.query(AccountsBoot).filter(AccountsBoot.username == account_info.login).update({
                            "balance": account_info.balance,
                            "equity": account_info.equity,
                            "margin": account_info.margin,
                            "free_margin": account_info.margin_free,
                            "leverage": account_info.leverage,
                            "server": account_info.server,
                        })

                    db.commit()

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
                ) for a in db.query(AccountsBoot).all()]

                position_data = [dict(
                    id=p.id,
                    id_transaction=p.id_transaction,
                    username=p.username,
                    position_type=p.position_type,
                    volume=p.volume,
                    symbol = p.symbol,
                    open_price=p.open_price,
                    current_price= p.current_price,
                    sl=p.sl,
                    tp=p.tp,
                    swap=p.swap,
                    profit=p.profit,
                    commission=p.profit,
                    magic_number=p.magic_number,
                    comment=p.comment
                ) for p in db.query(PositionBoot).all()]

                emit_sync("boot_monitor_acc", {"acc": acc_data, "position": position_data})
                    
            except Exception as e:
                db.rollback()
                print(f"[{name}] ❌ Lỗi trong monitor_account: {e}")
            finally:
                db.close()

            try:
                emit_boot_opposition_sync("boot_opposition", item)
            except Exception as e:
                print(f"❌ Lỗi emit_boot_opposition_sync: {e}")

    except KeyboardInterrupt:
        print("🔝 Logger process interrupted with Ctrl+C. Exiting gracefully.")
    finally:
        mt5.shutdown()