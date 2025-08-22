import re
import time
import json
import MetaTrader5 as mt5
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from datetime import datetime

from src.models.model import SessionLocal
from src.models.modelMultiAccountPnL import MultiAccountPnL

from src.models.modelTransaction.lot_information_model import LotInformation
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelTransaction.position_transaction_model import PositionTransaction
from src.models.modelTransaction.orders_transaction_model import OrdersTransaction
from src.models.modelTransaction.deal_transaction_model import DealTransaction

from src.services.terminals_transaction import terminals_transaction

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

def transaction_account_order(name, interval, stop_event):
    try: 
        while not stop_event.is_set():
            db = SessionLocal()

            try:
                dataLot = db.query(LotInformation).filter(LotInformation.account_transaction_id == int(name)).order_by(LotInformation.time.desc()).all()

                for item in dataLot:
                    status = item.status
                    account_monitor = item.account_monitor_id

                    switch_case = {
                        "Nguoc_Limit": partial(nguoc_limit_xuoi_stop, item, account_monitor),
                        "Xuoi_Stop": partial(nguoc_limit_xuoi_stop, item, account_monitor),

                        "Xuoi_Limit": partial(xuoi__limit_nguoc_stop, item, account_monitor),
                        "Nguoc_Stop": partial(xuoi__limit_nguoc_stop, item, account_monitor),
                    }

                    switch_case.get(status, partial(mac_dinh, item, account_monitor))()
                # print(f"✅ Theo dõi lot", status)
            except Exception as e:
                db.rollback()
                print(f"❌ Lỗi trong monitor_account: {e}")
            finally:
                db.close()
                time.sleep(interval)
    except KeyboardInterrupt:
        print("🔝 Logger process interrupted with Ctrl+C. Exiting gracefully.")
    finally:
        mt5.shutdown()

def pnl_monitor(id):
    db = SessionLocal()
    data = db.query(MultiAccountPnL).filter(MultiAccountPnL.login == id).order_by(MultiAccountPnL.time.desc()).first()
    db.close()
    return  data

def update_type_lot(id):
    db = SessionLocal()
    data = db.query(LotInformation).filter(LotInformation.id == id).update({"status": "Lenh_thi_truong"})
    db.commit()
    db.close()
    return data

def update_type_lot_type(id):
    db = SessionLocal()
    data = db.query(LotInformation).filter(LotInformation.id == id).update({"type": "CLOSE"})
    db.commit()
    db.close()
    return data

def close_send(dataSymbol: SymbolTransaction):
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
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # Gửi lệnh đóng
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise Exception(f"Gửi lệnh thất bại: {result.retcode} - {result.comment}")
    else:
        db.query(SymbolTransaction).filter(SymbolTransaction.id == dataSymbol.id).update({"status": "cancelled"})
        db.query(OrdersTransaction).filter(OrdersTransaction.id == dataSymbol.id).update({"status": "cancelled"})

        db.query(PositionTransaction).filter(PositionTransaction.id_transaction == ticket_id).delete()

        dataDeal = DealTransaction(
            username_id = dataSymbol.username_id,
            account_id = dataSymbol.account_transaction_id,
            symbol = dataSymbol.symbol,
            position_type = dataSymbol.type,
            volume = dataSymbol.volume,
            open_price = dataSymbol.price_open,
            close_price = price,
            open_time = datetime.fromtimestamp(pos.time),
            profit = pos.profit,
            swap = pos.swap,
            comment = pos.comment,
        )
        db.add(dataDeal)

        db.commit()
        db.close()
        return {"symbol": dataSymbol.symbol, "status": "success", "message": result}

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
        # ✅ chỉ commit khi tất cả run_order return success
        if all(r["status"] == "success" for r in results):
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

        results = []
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(run_order_close, dataLot) for dataLot in dataLots]
            for future in as_completed(futures):
                results.append(future.result())
        print("✅ vào lệnh trên MT5")
    finally:
        db.close()

def order_send_mt5(price: float, symbol: str, lot: float, order_type: str, id_symbol: int, acc_transaction: int):
    db = SessionLocal()

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        raise Exception(f"Không tìm thấy symbol: {symbol}")


    if not symbol_info.visible:
        mt5.symbol_select(symbol, True)

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise Exception(f"Không lấy được giá cho symbol: {symbol}")
    
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
        "symbol": symbol,
        "volume": lot,
        "type": mt5_order_type,
        "price": price,
        "slippage": 0,
        "magic": 123456,
        "comment": f"python-{symbol}",
        "type_time": ORDER_TIME_GTC,
        "type_filling": ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise Exception(f"Gửi lệnh thất bại: {result.retcode} - {result.comment}")
    else:
        ticket_id = result.order
        db.query(SymbolTransaction).filter(SymbolTransaction.id == id_symbol).update({"status": "filled", "symbol": symbol, "id_transaction": ticket_id})
        db.query(OrdersTransaction).filter(OrdersTransaction.id == id_symbol).update({"status": "filled", "id_transaction": ticket_id})
        db.commit()
        db.close()
        print("✅ Lệnh đã gửi:", result)
        return result
    
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
            futures = [executor.submit(run_order, order, json.loads(priceCurrentSymbls)[replace_suffix_with_m(order.symbol)]) for order in dataSymbolOpenSend]
            for future in as_completed(futures):
                results.append(future.result())

        # ✅ chỉ commit khi tất cả run_order return success
        if all(r["status"] == "success" for r in results):
            update_type_lot(id_lot)
        print("✅ vào lệnh trên MT5")
    finally:
        db.close()

# Hàm logic gửi yêu cầu mở lệnh theo giá so với PNL lên mt5
def nguoc_limit_xuoi_stop(item: LotInformation, account_monitor: int):
    # Với điều kiện PNL cao hơn PNL hiện tại, chờ giá giảm rồi bật lên
    data = pnl_monitor(account_monitor)
    if (item.price <= data.total_pnl):
        try: 
            open_order_mt5(acc_transaction=item.account_transaction_id, id_lot= item.id, priceCurrentSymbls= data.by_symbol)
            print("✅ Lệnh ngược limit")
        except Exception as e:
            print(f"Lỗi ở lệnh ngược limit: {e}")

def xuoi__limit_nguoc_stop(item: LotInformation, account_monitor: int):
    # điều kiện PNL thấp hơn PNL hiện tại, chờ giá giảm rồi bật lên
    data = pnl_monitor(account_monitor)
    if (item.price >= data.total_pnl):
        try: 
            open_order_mt5(acc_transaction=item.account_transaction_id, id_lot= item.id, priceCurrentSymbls= data.by_symbol)
            print("✅ Lệnh xuôi limit")
        except Exception as e:
            print(f"Lỗi ở lệnh xuôi limit: {e}")

# Hàm logic gửi yêu cầu đóng lệnh theo SL, TP so với PNL lên mt5
def mac_dinh(item: LotInformation, account_monitor: int):
# ngược: TP nằm dưới, SL nằm trên so với PNL
# xuôi: TP nằm trên, SL nằm dưới so với PNL
    data = pnl_monitor(account_monitor)
    pnl = data.total_pnl
    if (item.type == "RUNNING"): 
        if (item.status_sl_tp == "Xuoi"):
            if (pnl <= item.stop_loss or pnl >= item.take_profit):
                try:
                    close_order_mt5(id=item.id)
                    print("Đóng lệnh ở trạng thái lô xuôi: ")
                except Exception as e:
                    print(f"Lỗi ở đóng lệnh ở trạng thái lô xuôi: {e}")
        if (item.status_sl_tp == "Nguoc"):
            if (pnl >= item.stop_loss or pnl <= item.take_profit):
                try:
                    close_order_mt5(id=item.id)
                    print("Đóng lệnh ở trạng thái lô ngược: ")
                except Exception as e:
                    print(f"Lỗi ở đóng lệnh ở trạng thái lô ngược: {e}")
    else:
        print("Lệnh trên thị trường đã được đóng. Không thể thực hiện chức năng đóng tiếp!")