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
from src.models.modelTransaction.lot_information_model import LotInformation
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelTransaction.position_transaction_model import PositionTransaction
from src.models.modelTransaction.orders_transaction_model import OrdersTransaction

from src.services.terminals_transaction import terminals_transaction
from src.services.socket_manager import emit_sync, emit_data_compare_socket

from MetaTrader5 import (
    ORDER_TYPE_BUY, ORDER_TYPE_SELL,
    ORDER_FILLING_IOC, ORDER_TIME_GTC,
    TRADE_ACTION_DEAL, TRADE_ACTION_PENDING
)

# Khởi tạo MT5 1 lần khi app start
def mt5_connect(account_name: int):
    acc = terminals_transaction[str(account_name)]
    # Đóng kết nối cũ nếu đang mở
    mt5.shutdown()
    # Kết nối mới
    if not mt5.initialize(path=acc["path"], login=acc["login"], password=acc["password"], server=acc["server"]):
        raise Exception(f"Không connect được MT5 {account_name}. Lỗi: {mt5.last_error()}")
    return True

def auto_send_order_acc_transaction(pnl_q, stop_event):
    db = SessionLocal()
    while not stop_event.is_set():
        try:
            item_pnl_q = pnl_q.get(timeout=1)
        except pyqueue.Empty:
            continue
        try:
            data = item_pnl_q["data"] 
            dataLot = db.query(LotInformation).filter(LotInformation.account_monitor_id == int(data["login"]), LotInformation.type == "RUNNING").order_by(LotInformation.time.desc()).all()
            for item in dataLot:
                switch_case = {
                    "Nguoc_Limit": partial(nguoc_limit_xuoi_stop, item, data),
                    "Xuoi_Stop": partial(nguoc_limit_xuoi_stop, item, data),
                    "Xuoi_Limit": partial(xuoi__limit_nguoc_stop, item, data),
                    "Nguoc_Stop": partial(xuoi__limit_nguoc_stop, item, data),
                }
                switch_case.get(item.status, partial(mac_dinh, item, data))()
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
        db.query(LotInformation).filter(LotInformation.id == id).update({"status": "Lenh_thi_truong"})
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Lỗi ở lệnh ngược update_type_lot: {e}")
    finally:
        lot = db.query(LotInformation).filter(LotInformation.id == id).first()
        emit_sync("order_filled", {"status": "open_order", "data": model_to_dict(lot)})
        db.close()

def update_type_lot_type(id):
    db = SessionLocal()
    try: 
        db.query(LotInformation).filter(LotInformation.id == id).update({"type": "CLOSE"})
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Lỗi ở lệnh ngược update_type_lot_type: {e}")
    finally:
        lot = db.query(LotInformation).filter(LotInformation.id == id).first()
        emit_sync("order_filled", {"status": "close_order", "data": model_to_dict(lot)})
        db.close()

def isCheckServerAccTransac(usname: int) -> str:
    return terminals_transaction[str(usname)]["server"]

def close_send(dataSymbol: SymbolTransaction):
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
            db.query(SymbolTransaction).filter(SymbolTransaction.id == dataSymbol.id).update({"status": "cancelled"})
            db.query(OrdersTransaction).filter(OrdersTransaction.id == dataSymbol.id).update({"status": "cancelled"})

            db.query(PositionTransaction).filter(PositionTransaction.id_transaction == ticket_id).delete()

            db.commit()
        return {"symbol": dataSymbol.symbol, "status": "success", "message": result}
    except Exception as e:
        db.rollback()
        print(f"Lỗi ở close_send: {e}")
    finally:
        db.close()

def run_order_close(dataLot: LotInformation):
    mt5_connect(dataLot.account_transaction_id)
    db = SessionLocal()
    try:
        dataSymbols = db.query(SymbolTransaction).filter(
            SymbolTransaction.lot_id == dataLot.id,
            SymbolTransaction.status == "filled",
        ).order_by(SymbolTransaction.time.desc()).all()

        results = []

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(close_send, dataSymbol) for dataSymbol in dataSymbols]
            for future in as_completed(futures):
                results.append(future.result())
                
        # ✅ gom hết kết quả, chỉ update LotInformation khi tất cả success
        if all(r and r.get("status") == "success" for r in results):
            update_type_lot_type(dataLot.id)
        print("✅ vào lệnh trên MT5")
    finally:
        db.close()

def close_order_mt5(id: int):
    db = SessionLocal()
    try:
        dataLots = db.query(LotInformation).filter(
            LotInformation.id == id,
            LotInformation.status == "Lenh_thi_truong",
        ).order_by(LotInformation.time.desc()).all()

        return [run_order_close(dataLot) for dataLot in dataLots]
    finally:
        db.close()

def order_send_mt5(price: float, symbol: str, lot: float, order_type: str, id_symbol: int, acc_transaction: int):
    db = SessionLocal()
    try: 
        symbol_replace = symbol

        # CHU Y CHO NAY
        if "Exness" in isCheckServerAccTransac(acc_transaction):
            symbol_replace = replace_suffix_with___(symbol)

        symbol_info = mt5.symbol_info(symbol_replace)
        if symbol_info is None:
            raise Exception(f"Không tìm thấy symbol: {symbol_replace}")

        if not symbol_info.visible:
            mt5.symbol_select(symbol_replace, True)

        tick = mt5.symbol_info_tick(symbol_replace)
        if tick is None:
            raise Exception(f"Không lấy được giá cho symbol: {symbol_replace}")
        
        # Chuyển order_type từ chuỗi sang mã lệnh MT5
        order_type_map = {
            "BUY": ORDER_TYPE_BUY,
            "SELL": ORDER_TYPE_SELL,
        }

        if order_type not in order_type_map:
            raise Exception(f"Loại lệnh không hợp lệ: {order_type}")

        mt5_order_type = order_type_map[order_type]

        action_type = TRADE_ACTION_DEAL if order_type in ["BUY", "SELL"] else TRADE_ACTION_PENDING

        request = {
            "action": action_type,
            "symbol": symbol_replace,
            "volume": lot,
            "type": mt5_order_type,
            "price": price,
            "slippage": 0,
            "magic": 123456,
            "comment": f"python-{symbol_replace}",
            "type_time": ORDER_TIME_GTC,
            # "type_filling": ORDER_FILLING_IOC,
        }

        if "Exness" in isCheckServerAccTransac(acc_transaction):
            request["type_filling"] = ORDER_FILLING_IOC

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise Exception(f"Gửi lệnh thất bại: {result.retcode} - {result.comment}")
        else:
            ticket_id = result.order

            # Lấy thông tin lệnh để lấy profit
            pos = mt5.positions_get(ticket=ticket_id)
            profit = pos[0].profit if pos else 0

            db.query(SymbolTransaction).filter(SymbolTransaction.id == id_symbol).update({"status": "filled", "symbol": symbol_replace, "id_transaction": ticket_id, "profit": profit})
            db.query(OrdersTransaction).filter(OrdersTransaction.id == id_symbol).update({"status": "filled", "id_transaction": ticket_id, "profit": profit})
            db.commit()
            print("✅ Lệnh đã gửi:", result)
            return result
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi trong order_send_mt5: {e}")
    finally:
        db.close()

def run_order(order: SymbolTransaction, symbols_transaction):
    try:
        message = order_send_mt5(
            price=symbols_transaction["current_price"],
            symbol=replace_suffix_with(order.symbol),
            lot=order.volume,
            order_type=order.type,
            id_symbol=order.id,
            acc_transaction= order.account_transaction_id
        )
        return {"symbol": order.symbol, "status": "success", "message": message}
    except Exception as e:
        return {"symbol": order.symbol, "status": "error", "message": str(e)}

# bỏ hậu tố
def replace_suffix_with_m(sym: str) -> str:
    # Lấy phần chữ cái và số chính (base symbol)
    base = re.match(r"[A-Z]{6}", sym.upper())
    if base:
        return base.group(0) + "c"
    else:
        # Nếu không match (trường hợp đặc biệt) thì fallback
        return sym.rstrip("cm") + "c"

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


def normalize_symbols(data):
    new_data = {}
    for symbol, value in data.items():
        # Nếu symbol đúng 6 ký tự (chưa có hậu tố)
        if len(symbol) == 6:
            new_key = symbol + "c"
        else:
            new_key = symbol  # Đã có hậu tố rồi
        
        new_data[new_key] = value
    
    return new_data

def open_order_mt5(acc_transaction: int, id_lot: int, priceCurrentSymbls: str):
    mt5_connect(acc_transaction)

    db = SessionLocal()
    try:
        dataSymbolOpenSend = db.query(SymbolTransaction).filter(
            SymbolTransaction.lot_id == id_lot,
            SymbolTransaction.status == "pending",
        ).order_by(SymbolTransaction.time.desc()).all()

        results = []
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(run_order, order, normalize_symbols(json.loads(priceCurrentSymbls))[replace_suffix_with_m(order.symbol)]) for order in dataSymbolOpenSend]
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"❌ Lỗi trong thread run_order: {e}")
                    results.append({"status": "error", "message": str(e)})

        # ✅ chỉ commit khi tất cả run_order return success
        if all(r["status"] == "success" for r in results):
            update_type_lot(id_lot)
        print("✅ vào lệnh trên MT5")
    except Exception as e:
        print(f"Lỗi vào lệnh: {e}")
    finally:
        db.close()

# Hàm logic gửi yêu cầu mở lệnh theo giá so với PNL lên mt5
def nguoc_limit_xuoi_stop(item: LotInformation, data):
    if data:
        if (item.price <= data['total_pnl']):
            try: 
                open_order_mt5(acc_transaction=item.account_transaction_id, id_lot= item.id, priceCurrentSymbls= data['by_symbol'])
                print("✅ Lệnh xuoi__limit_nguoc_stop")
            except Exception as e:
                print(f"Lỗi ở lệnh ngược xuoi__limit_nguoc_stop: {e}")

def xuoi__limit_nguoc_stop(item: LotInformation, data):
    if data:
        if (item.price >= data['total_pnl']):
            try: 
                open_order_mt5(acc_transaction=item.account_transaction_id, id_lot= item.id, priceCurrentSymbls= data['by_symbol'])
                print("✅ Lệnh xuoi__limit_nguoc_stop")
            except Exception as e:
                print(f"Lỗi ở lệnh ngược xuoi__limit_nguoc_stop: {e}")

# Hàm logic gửi yêu cầu đóng lệnh theo SL, TP so với PNL lên mt5
def mac_dinh(item: LotInformation, data):
    if data:
        pnl = data['total_pnl']
        if (item.type == "RUNNING"): 
            if item.status_sl_tp in ["Xuoi_Limit", "Xuoi_Stop"]:
                if (pnl <= item.stop_loss or pnl >= item.take_profit):
                    try:
                        close_order_mt5(id=item.id)
                        print("Đóng lệnh ở trạng thái lô xuôi: ")
                    except Exception as e:
                        print(f"Lỗi ở đóng lệnh ở trạng thái lô xuôi: {e}")
            if item.status_sl_tp in ["Nguoc_Limit", "Nguoc_Stop"]:
                if (pnl >= item.stop_loss or pnl <= item.take_profit):
                    try:
                        close_order_mt5(id=item.id)
                        print("Đóng lệnh ở trạng thái lô ngược: ")
                    except Exception as e:
                        print(f"Lỗi ở đóng lệnh ở trạng thái lô ngược: {e}")
        else:
            print("Lệnh trên thị trường đã được đóng. Không thể thực hiện chức năng đóng tiếp!")

def send_socket_compare(pnl_queues_map, stop_event):
    while not stop_event.is_set():
        combined_data = []  # nơi gom toàn bộ PnL
        # duyệt qua tất cả account
        for name, pnl_q in pnl_queues_map.items():
            try:
                # lấy 1 item trong queue (nếu có)
                item_pnl_q = pnl_q.get(timeout=0.5)
                data = item_pnl_q.get("data", {})
                combined_data.append({
                    "login": name,
                    "total_pnl": data.get("total_pnl"),
                    "time": datetime.now().isoformat()
                })
            except pyqueue.Empty:
                # nếu queue trống -> bỏ qua
                continue
            except Exception as e:
                print(f"❌ Lỗi trong send_socket_compare ({name}): {e}")
                continue

        try:
            if combined_data:
                emit_data_compare_socket("data_compare_socket", combined_data)
        except Exception as e:
            print(f"❌ Lỗi emit_data_compare_socket: {e}")
        