from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from src.models.model import SessionLocal
from src.models.modelTransaction.schemas import CloseFastLotRequest, OrderBootItem, CloseOrderBootItem
from src.models.modelTransaction.lot_information_model import LotInformation
from src.models.modelBoot.position_transaction_model import PositionBoot

from src.controls.transaction_controls.auto_order import run_order_close

import MetaTrader5 as mt5
from src.services.terminals_transaction import terminals_transaction_boot
from src.utils.fund import replace_suffix_with_m

def run_lots(id_lot: int, id_user: int):
    db = SessionLocal()
    try:
        dataLots = db.query(LotInformation).filter(LotInformation.id == id_lot, LotInformation.username_id == id_user, LotInformation.status == "Lenh_thi_truong").order_by(LotInformation.time.desc()).all()
        results = []
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(run_order_close, dataLot) for dataLot in dataLots]
            for future in as_completed(futures):
                results.append(future.result())
        return results
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi trong đóng lệnh nhanh: {e}")
    finally:
        db.close()

# Khởi tạo MT5 1 lần khi app start
def mt5_connect(account_name: int):
    acc = terminals_transaction_boot[str(account_name)]
    # Đóng kết nối cũ nếu đang mở
    mt5.shutdown()
    # Kết nối mới
    if not mt5.initialize(path=acc["path"], login=acc["login"], password=acc["password"], server=acc["server"]):
        raise Exception(f"Không connect được MT5 {account_name}. Lỗi: {mt5.last_error()}")
    return True

def close_fast_lot_contronlls(datas: CloseFastLotRequest, current_user_id: int):
    results = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_lots, data.id, current_user_id) for data in datas]
        for future in as_completed(futures):
            results.append(future.result())
    return results

def run_boot_send_order(data: OrderBootItem):
    mt5_connect(data.username)
    try:
        symbol = replace_suffix_with_m(data.data.symbol)

        # Đảm bảo symbol đã được bật
        if not mt5.symbol_select(symbol, True):
            print(f"❌ Không chọn được symbol {symbol}")
            mt5.shutdown()
            return
        
        dataReq = data.data

        # mapping sang action
        if dataReq.type in [0, 1]:
            action = mt5.TRADE_ACTION_DEAL
        else:
            action = mt5.TRADE_ACTION_PENDING

        # Chuẩn bị request
        request = {
            "action": action,
            "symbol": symbol,
            "volume": dataReq.volume,
            "type": dataReq.type,
            "price": dataReq.price,
            "sl": dataReq.sl,
            "tp": dataReq.tp,
            "deviation": 10,
            "magic": 123456,
            "comment": "Auto order",
            "type_time": mt5.ORDER_TIME_GTC,   # Good till cancelled
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Gửi lệnh
        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Vào lệnh thất bại: {result}")
        else:
            print(f"✅ Vào lệnh thành công! Ticket: {result.order}")

    except Exception as e:
        print(f"❌ Lỗi trong đóng lệnh nhanh: {e}") 
    finally:
        # Đóng kết nối
        mt5.shutdown()

def send_order_boot(datas: List[OrderBootItem]):
    results = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_boot_send_order, data) for data in datas]
        for future in as_completed(futures):
            results.append(future.result())
    return results

def run_boot_close_order(data: CloseOrderBootItem):
    mt5_connect(data.serverName)
    try: 
        db = SessionLocal()

        # Lấy thông tin lệnh đang mở
        deviation = 30
        ticket_id = data.id
        
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
            db.query(PositionBoot).filter(PositionBoot.id_transaction == ticket_id).delete(synchronize_session=False)
            db.commit()

        return {"symbol": pos.volume, "status": "success", "message": result}
    except Exception as e:
        db.rollback()
        print(f"Lỗi ở close_send: {e}")
    finally:
        db.close()


def close_order_boot(datas: List[CloseOrderBootItem]):
    results = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_boot_close_order, data) for data in datas]
        for future in as_completed(futures):
            results.append(future.result())
    return results