import MetaTrader5 as mt5
from src.models.model import SessionLocal
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelBootAccMonitor.symbol_boot_monitor_model import SymbolMonitorBoot
from src.models.modelTransaction.lot_information_model import LotInformation
from src.models.modelTransaction.position_transaction_model import PositionTransaction
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.services.terminals_transaction import terminals_transaction
from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction
from src.models.modelTransaction.setting_close_odd import SettingCloseOddTransaction
from src.models.modelTransaction.setting_close_odd_daily_risk import SettingCloseOddDailyRiskTransaction
from src.models.modelTransaction.deal_transaction_model import DealTransaction
from src.models.modelTransaction.notification_transansaction import NotificationTransaction
from src.models.modelPNL import MultiAccountPnL_M1
from src.models.modelAccMt5 import AccountMt5
from src.services.socket_manager import emit_sync
from sqlalchemy import func
import json
from datetime import datetime
import queue as pyqueue

from src.controls.transaction_controls.auto_order import close_order_mt5

# Khởi tạo MT5 1 lần khi app start
def mt5_connect(account_name: int):
    acc = terminals_transaction[str(account_name)]
    # Đóng kết nối cũ nếu đang mở
    mt5.shutdown()
    # Kết nối mới
    if not mt5.initialize(path=acc['path']):
        raise Exception(f"Không connect được MT5 {account_name}. Lỗi: {mt5.last_error()}")
    return True

def close_positions_by_symbol(db, symbol: str, id_notification: int, account_transaction_id: int, deviation: int = 30):
    mt5_connect(account_transaction_id)
    try: 
        # Lấy tất cả position theo symbol
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return {"error": f"Không có lệnh nào với symbol {symbol}"}

        closed = []
        failed = []

        for pos in positions:
            # Xác định loại lệnh ngược lại để đóng
            close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY

            # Lấy giá hiện tại
            tick = mt5.symbol_info_tick(pos.symbol)
            if tick is None:
                failed.append({"ticket": pos.ticket, "error": "Không lấy được giá"})
                continue

            price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask

            # Tạo request đóng lệnh
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "position": pos.ticket,
                "price": price,
                "deviation": deviation,
                "magic": pos.magic,
                "comment": f"Close order {pos.ticket}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # Gửi lệnh đóng
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                closed.append(pos.ticket)
                db.query(PositionTransaction).filter(PositionTransaction.id_transaction == pos.ticket).delete()

                dataDeal = DealTransaction(
                    ticket = pos.ticket,
                    username_id = 1,
                    account_id = account_transaction_id,
                    symbol = pos.symbol,
                    position_type = close_type,
                    volume = pos.volume,
                    open_price = price,
                    close_price = price,
                    open_time = datetime.fromtimestamp(pos.time),
                    profit = pos.profit,
                    swap = pos.swap,
                    comment = pos.comment,
                    id_notification = id_notification
                )

                db.add(dataDeal)
            else:
                failed.append({"ticket": pos.ticket, "retcode": result.retcode, "comment": result.comment})
        db.commit()
        return {"closed": closed, "failed": failed}
    except Exception as e:
        db.rollback()
        print(f"Lỗi ở close_send: {e}")

def run_order(data: SymbolTransaction):
    db = SessionLocal()
    position = mt5.positions_get(ticket=data.id_transaction)
    result = None
    try:
        if position:
            pos = position[0]
            isPosition = db.query(PositionTransaction).filter(PositionTransaction.id_transaction == pos.ticket).order_by(PositionTransaction.time.desc()).first()
            dataSymbol = db.query(SymbolTransaction).filter(SymbolTransaction.id_transaction == pos.ticket).first()
            db.query(SymbolTransaction).filter(SymbolTransaction.id_transaction == pos.ticket).update({"profit": pos.profit})

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
                    profit=pos.profit,
                    is_odd = getattr(dataSymbol, "is_odd", False) if dataSymbol else False
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
                    profit = pos.profit,
                    is_odd = getattr(dataSymbol, "is_odd", False) if dataSymbol else False
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
                    profit=dataNew.profit,
                    is_odd=getattr(dataSymbol, "is_odd", False) if dataSymbol else False
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

                isCheckLo = db.query(LotInformation)\
                    .filter(LotInformation.account_transaction_id == account_info.login, 
                            LotInformation.IsUSD == True, 
                            LotInformation.type == "RUNNING",
                            LotInformation.status == "Lenh_thi_truong")\
                    .all()
                
                for item in isCheckLo:
                    profit_print = account_info.profit if account_info.login == item.account_transaction_id else None
                    if (item.usd >= profit_print):
                        close_order_mt5(item.id)

                dataOrder = db.query(SymbolTransaction).filter(SymbolTransaction.status == "filled").order_by(SymbolTransaction.time.desc()).all()
                dataOrderBoot = db.query(SymbolMonitorBoot).filter(SymbolMonitorBoot.status == "filled").order_by(SymbolMonitorBoot.time.desc()).all()

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
                
                # Gộp lại
                all_orders = dataOrder + dataOrderBoot

                results = []
                with ThreadPoolExecutor() as executor:
                    futures = [executor.submit(run_order, order) for order in all_orders]
                    for future in as_completed(futures):
                        if future.result():  # chỉ thêm nếu có dữ liệu
                            results.append(future.result())

                dataPosition = (
                    db.query(
                        PositionTransaction.symbol,
                        PositionTransaction.account_id,
                        func.sum(PositionTransaction.profit).label("total_profit"),
                        func.count(PositionTransaction.id).label("count_orders"),
                        func.sum(PositionTransaction.volume).label("total_volume")
                    )
                    .group_by(PositionTransaction.symbol, PositionTransaction.account_id)
                    .all()
                )

                dataAcc_transaction = (
                    db.query(
                        SettingCloseOddTransaction.risk,
                        AccountsTransaction.monney_acc,
                        AccountsTransaction.username,
                        SettingCloseOddDailyRiskTransaction.risk.label('daily_risk'),
                    )
                    .join(
                        SettingCloseOddTransaction,
                        AccountsTransaction.id_setting_close_odd == SettingCloseOddTransaction.id,
                    )
                    .join(
                        SettingCloseOddDailyRiskTransaction,
                        AccountsTransaction.id_setting_close_odd_daily_risk == SettingCloseOddDailyRiskTransaction.id,
                    )
                ).all()

                isCheckLoAccTransaction = db.query(LotInformation).filter(LotInformation.account_transaction_id == int(account_info.login), 
                                                                          LotInformation.status == "Lenh_thi_truong").all()
                if (isCheckLoAccTransaction):
                    for item in isCheckLoAccTransaction:
                        isSymbolLot = db.query(SymbolTransaction).filter(SymbolTransaction.lot_id == item.id, SymbolTransaction.status == "cancelled").all()
                        isAccMonitor = db.query(AccountMt5).filter(AccountMt5.username == item.account_monitor_id).first()
                        if (len(isSymbolLot) >= len(json.loads(isAccMonitor.by_symbol))):
                            db.query(LotInformation).filter(LotInformation.id == item.id).update({"type": "CLOSE"})
                    db.commit()

                today = datetime.now().date()
                start = datetime.combine(today, datetime.min.time())   # 00:00:00 hôm nay
                end   = datetime.combine(today, datetime.max.time())   # 23:59:59 hôm nay

                symbolRisk = []
                for risk, monney_acc, username, daily_risk in dataAcc_transaction:
                    total_profit = (
                        db.query(func.sum(SymbolTransaction.profit))
                        .filter(
                            SymbolTransaction.account_transaction_id == username,
                            SymbolTransaction.time >= start,
                            SymbolTransaction.time <= end
                        )
                        .scalar()  # trả về 1 giá trị thay vì tuple
                    )
                    filtered = [row for row in dataPosition if int(row[1]) == int(username)]
                    if (total_profit):
                        if (total_profit <= -(monney_acc * (daily_risk / 100))):
                            for row in filtered:
                                dataSendOrder = close_positions_by_symbol(db, symbol= row[0], id_notification= 1, account_transaction_id= username)
                                if (dataSendOrder['closed']):
                                    dataNotification = NotificationTransaction(
                                        loginId = 1,
                                        account_transaction_id = username,
                                        symbol = row[0],
                                        total_volume = row[4],
                                        profit = row[2],
                                        total_order = row[3],
                                        risk = risk,
                                        monney_acctransaction = monney_acc,
                                        is_send= False,
                                        isRead= False,
                                        daily_risk= daily_risk,
                                        type_notification = "daily"
                                    )
                                    db.add(dataNotification)
                                    db.flush()

                                    emit_sync("notification_message", dataNotification.to_dict())

                                    for a in dataSendOrder['closed']:
                                        print(a, row[0], "profit: ", row[2])
                                        db.query(DealTransaction).filter(DealTransaction.ticket == a).update({"id_notification": dataNotification.id})
                                        db.query(SymbolTransaction).filter(SymbolTransaction.id_transaction == a).update({"status": "cancelled"})
                                        
                                    db.commit()

                    for row in filtered:
                        symbolRisk.append({
                            "acc": username,
                            "symbol": row[0],
                            "total_volume": row[4],
                            "total_profit": row[2],
                            "total_order": row[3],
                            "monney_acctransaction": monney_acc,
                            "risk": risk,
                            "daily_risk": daily_risk,
                            "daily_profit": total_profit,
                        })
                        if (row[2] <= -(monney_acc * (risk / 100))):
                            dataSendOrder = close_positions_by_symbol(db, symbol= row[0], id_notification= 1, account_transaction_id= username)
                            if (dataSendOrder['closed']):
                                dataNotification = NotificationTransaction(
                                    loginId = 1,
                                    account_transaction_id = username,
                                    symbol = row[0],
                                    total_volume = row[4],
                                    profit = row[2],
                                    total_order = row[3],
                                    risk = risk,
                                    monney_acctransaction = monney_acc,
                                    is_send=False,
                                    isRead=False,
                                    daily_risk= daily_risk,
                                    type_notification = "risk"
                                )
                                db.add(dataNotification)
                                db.flush()

                                emit_sync("notification_message", dataNotification.to_dict())

                                for a in dataSendOrder['closed']:
                                    print(a, row[0], "profit: ", row[2])
                                    db.query(DealTransaction).filter(DealTransaction.ticket == a).update({"id_notification": dataNotification.id})
                                    db.query(SymbolTransaction).filter(SymbolTransaction.id_transaction == a).update({"status": "cancelled"})
                                    
                                db.commit()
                                
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
                        data_pnl_monitor = db.query(MultiAccountPnL_M1).filter(MultiAccountPnL_M1.login == row.account_monitor).order_by(MultiAccountPnL_M1.id.desc()).first()
                        break_even.append({
                            "account_monitor": row.account_monitor,
                            "account_transaction": row.account_transaction,
                            "total_volume": row.total_volume,
                            "type": row.account_start,
                            "total_order": row.record_count,
                            "total_profit": profit,
                            "pnl_break_even": profit / (row.total_volume * 100) if row.total_volume != 0 else 0,
                            "pnl": data_pnl_monitor.close if data_pnl_monitor else 0
                        })
                
                emit_sync("position_message", {"acc": acc_data, "positions": results, "break_even": break_even, "symbolRisk": symbolRisk})
            except Exception as e:
                db.rollback()
                print(f"[{name}] ❌ Lỗi trong monitor_account: {e}")
            finally:
                db.close()
    except KeyboardInterrupt:
        print("🔝 Logger process interrupted with Ctrl+C. Exiting gracefully.")
    finally:
        mt5.shutdown()