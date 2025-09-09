import time
import MetaTrader5 as mt5
from src.models.model import SessionLocal
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelTransaction.lot_information_model import LotInformation
from src.models.modelTransaction.position_transaction_model import PositionTransaction
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.services.terminals_transaction import terminals_transaction
from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction
from src.models.modelMultiAccountPnL import MultiAccountPnL
from src.services.socket_manager import emit_sync
from sqlalchemy import func
import json
import queue as pyqueue

# Khởi tạo MT5 1 lần khi app start
def mt5_connect(account_name: int):
    acc = terminals_transaction[str(account_name)]
    # Đóng kết nối cũ nếu đang mở
    mt5.shutdown()
    # Kết nối mới
    if not mt5.initialize(path=acc['path']):
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

def auto_position(name, cfg, queue, stop_event, pub_queue):
    mt5_connect(name)
    try: 
        while not stop_event.is_set():
            db = SessionLocal()
            try:
                queue.get(timeout=1)
            except pyqueue.Empty:
                # không có tín hiệu mới → bỏ qua vòng lặp
                continue
            try:

                account_info = mt5.account_info()

                dataOrder = db.query(SymbolTransaction).filter(SymbolTransaction.status == "filled").order_by(SymbolTransaction.time.desc()).all()

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

                break_even = []
                for item in acc_data:
                    # Subquery đầu tiên: tính total_open_price theo lot_id
                    subq_positions = (
                        db.query(
                            SymbolTransaction.lot_id.label("lot_id"),
                            func.sum(PositionTransaction.profit).label("total_open_price")
                        )
                        .join(PositionTransaction, PositionTransaction.id_transaction == SymbolTransaction.id_transaction)
                        .group_by(SymbolTransaction.lot_id)
                        .subquery()
                    )

                    # Subquery thứ 2: group theo account_monitor_id, account_transaction_id, status_sl_tp
                    subq_total_profit = (
                        db.query(
                            LotInformation.account_monitor_id.label("account_monitor"),
                            LotInformation.account_transaction_id.label("account_transaction"),
                            LotInformation.status_sl_tp.label("status_sl_tp"),
                            func.sum(subq_positions.c.total_open_price).label("total_profit"),
                        )
                        .join(subq_positions, subq_positions.c.lot_id == LotInformation.id)
                        .group_by(
                            LotInformation.account_monitor_id,
                            LotInformation.account_transaction_id,
                            LotInformation.status_sl_tp
                        )
                        .subquery()
                    )

                    # Query cuối cùng: chỉ select ra các cột bạn muốn
                    result_total_profit = (
                        db.query(
                            subq_total_profit.c.account_monitor,
                            subq_total_profit.c.account_transaction,
                            subq_total_profit.c.status_sl_tp,
                            subq_total_profit.c.total_profit,
                        )
                        .all()
                    )

                    subq_total_volume = (
                        db.query(
                            LotInformation.account_monitor_id.label("account_monitor"),
                            LotInformation.account_transaction_id.label("account_transaction"),
                            LotInformation.status_sl_tp.label("account_start"),
                            func.sum(LotInformation.volume).label("total_volume"),
                            func.count(LotInformation.id).label("record_count"),
                        )
                        .filter(LotInformation.account_transaction_id == item["username"], 
                                LotInformation.status == "Lenh_thi_truong", 
                                LotInformation.type == "RUNNING")
                        .group_by(LotInformation.account_monitor_id, 
                                  LotInformation.account_transaction_id,
                                  LotInformation.status_sl_tp)
                        .subquery()
                    )

                    result_total_volume = (
                        db.query(
                            subq_total_volume.c.account_monitor,
                            subq_total_volume.c.account_transaction,
                            subq_total_volume.c.total_volume,
                            subq_total_volume.c.account_start,
                            subq_total_volume.c.record_count, 
                        )
                        .all()
                    )

                    profit_map = {
                        (monitor, transaction, sl_tp): profit
                        for monitor, transaction, sl_tp, profit in result_total_profit
                    }
                    
                    for row in result_total_volume:
                        profit = profit_map.get((row.account_monitor, row.account_transaction, row.account_start), 0)
                        data_pnl_monitor = db.query(MultiAccountPnL).filter(MultiAccountPnL.login == row.account_monitor).order_by(MultiAccountPnL.id.desc()).first()
                        break_even.append({
                            "account_monitor": row.account_monitor,
                            "account_transaction": row.account_transaction,
                            "total_volume": row.total_volume,
                            "type": row.account_start,
                            "total_order": row.record_count,
                            "total_profit": profit,
                            "pnl_break_even": profit / (row.total_volume * 100) if row.total_volume != 0 else 0,
                            "pnl": data_pnl_monitor.total_pnl if data_pnl_monitor else 0
                        })
                emit_sync("position_message", {"acc": acc_data, "positions": results, "break_even": break_even})
            except Exception as e:
                db.rollback()
                print(f"[{name}] ❌ Lỗi trong monitor_account: {e}")
            finally:
                db.close()
    except KeyboardInterrupt:
        print("🔝 Logger process interrupted with Ctrl+C. Exiting gracefully.")
    finally:
        mt5.shutdown()