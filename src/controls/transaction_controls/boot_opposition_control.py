import MetaTrader5 as mt5
import queue as pyqueue
from src.services.terminals_transaction import terminals_transaction
from src.services.socket_manager import emit_boot_opposition_sync
from src.models.model import SessionLocal
from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction
from src.models.modelBoot.position_transaction_model import PositionBoot
from src.models.modelBoot.orders_transaction_model import OrdersBoot
from src.models.modelBoot.info_lo_transaction_model import InfoLoTransactionBoot
from src.services.socket_manager import emit_sync
from src.utils.account_filtering import account_filtering
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Khởi tạo MT5 1 lần khi app start
def mt5_connect(account_name: int):
    acc = terminals_transaction[str(account_name)]
    # Đóng kết nối cũ nếu đang mở
    mt5.shutdown()
    # Kết nối mới
    if not mt5.initialize(path=acc['path']):
        raise Exception(f"Không connect được MT5 {account_name}. Lỗi: {mt5.last_error()}")
    return True

def mt5_connect_boot(account_name, cfg):
    if not mt5.initialize(path=cfg["path"], login=cfg["login"], password=cfg["password"], server=cfg["server"]):
        print(f"[{account_name}] ❌ Không kết nối được MT5")
        return False
    return True

def boot_auto_opposition(name, cfg, queue, stop_event, pub_queue):
    mt5_connect(name)
    try: 
        while not stop_event.is_set():
            db = SessionLocal()
            try:
                item = queue.get(timeout=1)
            except pyqueue.Empty:
                pass

            try:
                positions = mt5.positions_get()
                account_info = mt5.account_info()
                acc = account_filtering()

                if account_info is not None:
                    if account_info.login in acc:
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
                                    db.query(OrdersBoot).filter(OrdersBoot.id_transaction == int(pos.ticket)).update({
                                        "profit": pos.profit,
                                        "price_market": pos.price_current
                                    })
                                db.commit()

                        if (account_info):
                            db.query(AccountsTransaction).filter(AccountsTransaction.username == account_info.login, 
                                                                 AccountsTransaction.loginId == 1).update({
                                    "balance": account_info.balance,
                                    "equity": account_info.equity,
                                    "margin": account_info.margin,
                                    "free_margin": account_info.margin_free,
                                    "leverage": account_info.leverage
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
                        ) for a in db.query(AccountsTransaction).filter(AccountsTransaction.loginId == 1, AccountsTransaction.type_acc == "RECIPROCAL").all()]

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

def close_sync_worker(terminals, close_sync_queue, stop_event):
    # Trạng thái lệnh hiện tại của từng account
    # tracked_positions[account] = set((symbol, type))
    tracked_positions = {acc: set() for acc in terminals.keys()}

    while not stop_event.is_set():
        try:
            event = close_sync_queue.get(timeout=1)
        except:
            continue

        try:
            db = SessionLocal()
            source = event.get("account")
            action = event.get("action")

            # --- CLOSE EVENT ---
            if action == "close":
                symbol = event["symbol"]
                pos_type = event["type"]
                pos_ticket= event["ticket"]

                for acc, cfg in terminals.items():
                    if acc == source:
                        continue
                    # if (symbol, pos_type) in tracked_positions[acc]:
                    try:
                        print(f"[SYNC] Closing {symbol} type={pos_type} on {acc}; {pos_ticket}")

                        isCheckOrderBoot = db.query(OrdersBoot).filter(OrdersBoot.id_transaction == pos_ticket).first()

                        dataOrderBoots = db.query(OrdersBoot).filter(OrdersBoot.lo_boot_id == isCheckOrderBoot.lo_boot_id).all()
                        results = []
                        with ThreadPoolExecutor() as executor:
                            futures = [executor.submit(close_order, dataOrderBoot.account_id, dataOrderBoot.symbol) for dataOrderBoot in dataOrderBoots]
                            for future in as_completed(futures):
                                results.append(future.result())
                            # ✅ chỉ commit khi tất cả run_order return success
                            if (r["status"] == "success" for r in results):
                                for dataOrderBoot in dataOrderBoots:
                                    db.query(PositionBoot).filter(PositionBoot.id_transaction == dataOrderBoot.id_transaction).delete()
                                    db.query(OrdersBoot).filter(OrdersBoot.id_transaction == dataOrderBoot.id_transaction).update({"status": "cancelled"})
                                db.query(InfoLoTransactionBoot).filter(InfoLoTransactionBoot.id == isCheckOrderBoot.lo_boot_id).update({"type": "CLOSE"})
                                db.commit()
                        # close_order(acc, symbol)

                        tracked_positions[acc].discard((symbol, pos_type))
                    except Exception as e:
                        print(f"[ERROR] sync close {symbol} on {acc}:", e)

                # update source cũng loại bỏ lệnh đó
                tracked_positions[source].discard((symbol, pos_type))

            # --- OPEN EVENT ---
            elif action == "open":
                symbol = event["symbol"]
                volume = event["volume"]
                pos_type = event["type"]

                # Xác định loại đối ứng
                opposite_type = mt5.POSITION_TYPE_SELL if pos_type == mt5.POSITION_TYPE_BUY else mt5.POSITION_TYPE_BUY

                for acc, cfg in terminals.items():
                    if acc == source:
                        continue
                    if (symbol, opposite_type) not in tracked_positions[acc]:
                        try:
                            print(f"[SYNC] Opening {symbol} vol={volume} type={opposite_type} on {acc}")
                            # open_order(acc, cfg, symbol, volume, pos_type)  # vẫn truyền pos_type gốc, open_order sẽ đảo
                            tracked_positions[acc].add((symbol, opposite_type))
                        except Exception as e:
                            print(f"[ERROR] sync open {symbol} on {acc}:", e)

                # update source theo chiều gốc
                tracked_positions[source].add((symbol, pos_type))

        except Exception as e:
            db.rollback()
            print(f"Lỗi ở close_sync_worker: {e}")
        finally:
            db.close()

def close_order(account, symbol):
    mt5_connect(account)
    try: 
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            print(f"[{account}] ❌ Không tìm thấy position {symbol}")
            return

        tick = mt5.symbol_info_tick(symbol)

        pos = positions[0]
        price = tick.ask if pos.type == mt5.POSITION_TYPE_SELL else tick.bid

        order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": order_type,
            "position": pos.ticket,
            "price": price,
            "magic": 123456,
            "comment": "sync close",
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise Exception(f"Gửi lệnh thất bại: {result.retcode} - {result.comment}")
        else:
            return {"result": result, "status": "success"}
    except Exception as e:
        print(f"Lỗi ở close_send: {e}")

def open_order(account, cfg, symbol, volume, pos_type):
    mt5_connect_boot(account, cfg)

    # Lấy info symbol
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if not info or not tick:
        print(f"[{account}] Không lấy được giá {symbol}")
        return

    # Đảo chiều lệnh
    order_type = mt5.ORDER_TYPE_SELL if pos_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

    pip = 1.0
    tp_distance = 62.5 * pip
    sl_distance = 63 * pip

    # Tính SL/TP
    if order_type == mt5.ORDER_TYPE_BUY:
        sl = round(price - sl_distance, info.digits)
        tp = round(price + tp_distance, info.digits)
    else:
        sl = round(price + sl_distance, info.digits)
        tp = round(price - tp_distance, info.digits)

    # Tự set khoảng cách tối thiểu (ví dụ 10 USD cho BTCUSDm)
    min_stop_distance = 10.0
    if abs(price - sl) < min_stop_distance or abs(tp - price) < min_stop_distance:
        print(f"[{account}] SL/TP quá gần, bỏ qua đặt SL/TP hoặc tăng khoảng cách")
        sl, tp = 0.0, 0.0  # Có thể chọn không đặt SL/TP

    # Volume nhân 3.75 và làm tròn theo step
    step = info.volume_step
    new_volume = round(volume * 3.75 / step) * step
    new_volume = max(info.volume_min, min(new_volume, info.volume_max))

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": new_volume,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 100,
        "magic": 123456,
        "comment": "sync open",
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    print(f"[{account}] Open {symbol} vol={volume} type={pos_type} result:", result)