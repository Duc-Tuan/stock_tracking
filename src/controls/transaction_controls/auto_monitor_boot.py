import re
import time
import json
import MetaTrader5 as mt5
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from datetime import datetime
from requests import session
import queue as pyqueue

from src.models.model import SessionLocal
from src.models.modelBootAccMonitor.info_boot_monitor_model import InfoBootMonitorBoot
from src.models.modelBootAccMonitor.symbol_boot_monitor_model import SymbolMonitorBoot
from src.models.modelBootAccMonitor.position_boot_monitor_model import PositionMonitorBoot

from src.services.terminals_transaction import terminals_transaction
from src.services.socket_manager import emit_sync, emit_data_compare_socket

# Khởi tạo MT5 1 lần khi app start
def mt5_connect(account_name: int):
    acc = terminals_transaction[str(account_name)]
    # Đóng kết nối cũ nếu đang mở
    mt5.shutdown()
    # Kết nối mới
    if not mt5.initialize(path=acc["path"], login=acc["login"], password=acc["password"], server=acc["server"]):
        raise Exception(f"Không connect được MT5 {account_name}. Lỗi: {mt5.last_error()}")
    return True

def auto_close_tp_monitor_boot(pnl_q, stop_event):
    db = SessionLocal()
    while not stop_event.is_set():
        try:
            item_pnl_q = pnl_q.get(timeout=1)
        except pyqueue.Empty:
            continue
        try:
            data = item_pnl_q["data"] 
            dataLot = db.query(InfoBootMonitorBoot).filter(InfoBootMonitorBoot.acc_monitor == int(data["login"]), InfoBootMonitorBoot.type == "RUNNING").order_by(InfoBootMonitorBoot.time.desc()).all()
            for item in dataLot:
                switch_case_reference = {
                    "XUOI": partial(xuoi, item, item.acc_reference, item.tp_acc_reference, data),
                    "NGUOC": partial(nguoc, item, item.acc_reference, item.tp_acc_reference, data),
                }
                switch_case_reference.get(item.type_acc_reference, partial(mac_dinh))()

                switch_case_reciprocal = {
                    "XUOI": partial(xuoi, item, item.acc_reciprocal, item.tp_acc_reciprocal, data),
                    "NGUOC": partial(nguoc, item, item.acc_reciprocal, item.tp_acc_reciprocal, data),
                }
                switch_case_reciprocal.get(item.type_acc_reciprocal, partial(mac_dinh))()
                
        except Exception as e:
            session.rollback()
            print(f"❌ Lỗi trong auto_send_order_acc_transaction: {e}")
            continue
        finally:
            db.close()

def model_to_dict(obj):
    result = {}
    for c in obj.__table__.columns:
        value = getattr(obj, c.name)
        if isinstance(value, datetime):
            result[c.name] = value.isoformat()   # hoặc str(value)
        else:
            result[c.name] = value
    return result

def update_type_lot(id):
    db = SessionLocal()
    try: 
        db.query(InfoBootMonitorBoot).filter(InfoBootMonitorBoot.id == id).update({"type": "CLOSE"})
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Lỗi ở lệnh ngược update_type_lot_boot: {e}")
    finally:
        lot = db.query(InfoBootMonitorBoot).filter(InfoBootMonitorBoot.id == id).first()
        emit_sync("order_filled", {"status": "open_order_boot", "data": model_to_dict(lot)})
        db.close()

def isCheckServerAccTransac(usname: int) -> str:
    return terminals_transaction[str(usname)]["server"]

def close_send(dataSymbol: SymbolMonitorBoot):
    try: 
        db = SessionLocal()

        # Lấy thông tin lệnh đang mở
        deviation = 30
        ticket_id = dataSymbol.id_transaction
        
        position = mt5.positions_get(ticket=ticket_id)
        if not position:
            return {"error": f"Không tìm thấy lệnh với ticket {ticket_id}"}

        pos = position[0]

        # Xác định loại lệnh đóng (ngược lại)
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY

        # Lấy giá hiện tại
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            return {"error": f"Không lấy được giá cho {pos.symbol}"}

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
            # "type_filling": mt5.ORDER_FILLING_IOC,
        }

        if "Exness" in isCheckServerAccTransac(dataSymbol.account_transaction_id):
            request["type_filling"] = mt5.ORDER_FILLING_IOC

        # Gửi lệnh đóng
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise Exception(f"Gửi lệnh thất bại: {result.retcode} - {result.comment}")
        else:
            db.query(SymbolMonitorBoot).filter(SymbolMonitorBoot.id_transaction == ticket_id).update({"status": "cancelled"})
            # db.query(PositionMonitorBoot).filter(PositionMonitorBoot.id_transaction == ticket_id).delete()

            db.commit()
        return {"symbol": dataSymbol.symbol, "status": "success", "message": result}
    except Exception as e:
        db.rollback()
        print(f"Lỗi ở close_send: {e}")
    finally:
        db.close()

def run_order(order: SymbolMonitorBoot):
    try:
        message = close_send(order)
        return {"symbol": order.symbol, "status": "success", "message": message}
    except Exception as e:
        return {"symbol": order.symbol, "status": "error", "message": str(e)}

def replace_suffix_with(sym: str) -> str:
    # Lấy phần chữ cái và số chính (base symbol)
    base = re.match(r"[A-Z]{6}", sym.upper())
    if base:
        return base.group(0)  + "m"
    else:
        # Nếu không match (trường hợp đặc biệt) thì fallback
        return sym.rstrip("cm")  + "m"

def replace_suffix_with___(sym: str) -> str:
    # Lấy phần chữ cái và số chính (base symbol)
    base = re.match(r"[A-Z]{6}", sym.upper())
    if base:
        return base.group(0)
    else:
        # Nếu không match (trường hợp đặc biệt) thì fallback
        return sym.rstrip("cm")

def close_order_mt5(acc_transaction: int, id_lot: int):
    mt5_connect(acc_transaction)

    db = SessionLocal()
    try:
        dataSymbolOpenSend = db.query(SymbolMonitorBoot).filter(
            SymbolMonitorBoot.lot_id == id_lot,
        ).order_by(SymbolMonitorBoot.time.desc()).all()

        results = []
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(run_order, order) for order in dataSymbolOpenSend]
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"❌ Lỗi trong thread open_order_mt5_boot: {e}")
                    results.append({"status": "error", "message": str(e)})

        if all(r["status"] == "success" for r in results):
            if all(r.status == "cancelled" for r in dataSymbolOpenSend):
                update_type_lot(id_lot)
    except Exception as e:
        print(f"Lỗi vào lệnh: {e}")
    finally:
        db.close()

# Hàm logic gửi yêu cầu mở lệnh theo giá so với PNL lên mt5
def xuoi(item: InfoBootMonitorBoot, acc, tp, data):
    if data:
        if (tp <= data['total_pnl']):
            try: 
                close_order_mt5(acc_transaction=acc, id_lot= item.id)
            except Exception as e:
                print(f"Lỗi ở lệnh xuôi: {e}")

def nguoc(item: InfoBootMonitorBoot, acc, tp, data):
    if data:
        if (tp >= data['total_pnl']):
            try: 
                close_order_mt5(acc_transaction=acc, id_lot= item.id)
            except Exception as e:
                print(f"Lỗi ở lệnh ngược: {e}")

# Hàm logic gửi yêu cầu đóng lệnh theo SL, TP so với PNL lên mt5
def mac_dinh():
    print("Đang chờ...")
        