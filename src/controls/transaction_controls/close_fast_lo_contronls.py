from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from src.models.model import SessionLocal
from src.models.modelTransaction.schemas import CloseFastLotRequest, OrderBootItem, CloseOrderBootItem, CloseOrderBoot
from src.models.modelTransaction.lot_information_model import LotInformation
from src.models.modelBoot.info_lo_transaction_model import InfoLoTransactionBoot
from src.models.modelBoot.position_transaction_model import PositionBoot
from src.models.modelBoot.orders_transaction_model import OrdersBoot
from datetime import datetime
from src.controls.transaction_controls.auto_order import run_order_close
from sqlalchemy import func
import MetaTrader5 as mt5
from src.services.terminals_transaction import terminals_transaction_boot
from src.utils.fund import replace_suffix_with_m
import re
from src.services.terminals_transaction import terminals_transaction
from fastapi import HTTPException

from MetaTrader5 import (
    ORDER_TYPE_BUY, ORDER_TYPE_SELL,
    ORDER_FILLING_IOC, ORDER_TIME_GTC,
    TRADE_ACTION_DEAL, TRADE_ACTION_PENDING
)


def replace_suffix_with_(sym: str) -> str:
    # Lấy phần chữ cái và số chính (base symbol)
    base = re.match(r"[A-Z]{6}", sym.upper())
    if base:
        return base.group(0)  + "_"
    else:
        # Nếu không match (trường hợp đặc biệt) thì fallback
        return sym.rstrip("cm")  + "_"
    
def replace_suffix_with(sym: str) -> str:
    # Lấy phần chữ cái và số chính (base symbol)
    base = re.match(r"[A-Z]{6}", sym.upper())
    if base:
        return base.group(0)
    else:
        # Nếu không match (trường hợp đặc biệt) thì fallback
        return sym.rstrip("cm")
    
def run_lots(id_lot: int, id_user: int):
    db = SessionLocal()
    try:
        dataLots = db.query(LotInformation).filter(LotInformation.id == id_lot, LotInformation.username_id == id_user, LotInformation.status == "Lenh_thi_truong").order_by(LotInformation.time.desc()).all()
        results = [run_order_close(dataLot) for dataLot in dataLots]
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
    results = [run_lots(data.id, current_user_id) for data in datas]
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
        print(f"❌ Lỗi trong vào lệnh: {e}") 
    finally:
        # Đóng kết nối
        mt5.shutdown()

def send_order_boot(datas: List[OrderBootItem], id: int):
    try:
        db = SessionLocal()

        exness_orders = [o for o in datas if o.type == 'EXNESS'][0]
        fund_orders = [o for o in datas if o.type == 'FUND'][0]
        dataNew = InfoLoTransactionBoot(
            login_id = 1,
            acc_reference = exness_orders.username,
            acc_reciprocal = fund_orders.username,
            type = "RUNNING"
        )
        db.add(dataNew)
        db.flush()

        results = []
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(run_boot_run_order, data, dataNew.id, id) for data in datas]
            for future in as_completed(futures):
                results.append(future.result())
            
            # ✅ chỉ commit khi tất cả run_order return success
            if (r["status"] == "success" for r in results):
                for r in results:
                    dataNewOrder = r["data"]
                    db.add(dataNewOrder)
                db.commit()
        return {"status": "success", "results": results}
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi trong vào lệnh: {e}") 
    finally:
        db.close()

def isCheckServerAccTransac(usname: int) -> str:
    return terminals_transaction[str(usname)]["server"]

def run_boot_run_order(data: OrderBootItem, id_Lot: int, user_id: int):
    mt5_connect(data.username)
    try: 
        symbol = data.data.symbol
        lot = data.data.volume
        sl = data.data.sl
        tp = data.data.tp
        price = data.data.price
        order_type = "BUY" if (data.data.type == 0) else "SELL"
        symbol_replace = replace_suffix_with_m(symbol)

        # if "Exness" in isCheckServerAccTransac(data.username):
        #     symbol_replace = replace_suffix_with(symbol)

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

        # Nếu không có price thì lấy giá thị trường
        if price is None:
            if order_type == "BUY":
                price = tick.ask
            elif order_type == "SELL":
                price = tick.bid

        request = {
            "action": action_type,
            "symbol": symbol_replace,
            "volume": lot,
            "type": mt5_order_type,
            "price": price,
            "slippage": 0,
            "sl": sl,
            "tp": tp,
            "magic": 123456,
            "comment": f"python-{symbol}",
            "type_time": ORDER_TIME_GTC,
        }

        if "Exness" in isCheckServerAccTransac(data.username):
            request["type_filling"] = ORDER_FILLING_IOC

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise Exception(f"Gửi lệnh thất bại: {result.retcode} - {result.comment}")
        else:
            ticket_id = result.order
            dataNewOrder = OrdersBoot(
                id_transaction= ticket_id,
                lo_boot_id = id_Lot,
                user_id = user_id,
                account_id = data.username,
                symbol = symbol_replace,
                order_type = order_type,
                volume = lot,
                sl = sl,
                tp = tp,
                price = price,
                price_market = price,
                type_acc = data.type,
                status = "filled"
            )
        return {"result": result, "status": "success", "data": dataNewOrder}
    except Exception as e:
        print(f"Lỗi ở close_send: {e}")

def run_boot_close_order(data):
    mt5_connect(data.account_id)
    try: 
        db = SessionLocal()

        # Lấy thông tin lệnh đang mở
        deviation = 30
        ticket_id = data.id_transaction
        
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
            db.query(OrdersBoot).filter(OrdersBoot.id_transaction == ticket_id).update({"status": "cancelled"})
            db.commit()

        return {"symbol": pos.volume, "status": "success", "message": result}
    except Exception as e:
        db.rollback()
        print(f"Lỗi ở close_send: {e}")
    finally:
        db.close()

def close_order_boot(datas: CloseOrderBoot):
    try:
        db = SessionLocal()
        isCheck = db.query(InfoLoTransactionBoot).filter(InfoLoTransactionBoot.id == datas.id, InfoLoTransactionBoot.type == 'RUNNING').first()
        if (isCheck):
            orderBoots = db.query(OrdersBoot).filter(OrdersBoot.lo_boot_id == isCheck.id, OrdersBoot.status == 'filled').all()
            results = []
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(run_boot_close_order, orderBoot) for orderBoot in orderBoots]
                for future in as_completed(futures):
                    results.append(future.result())
            if (r and r.get("status") == "success" for r in results):
                db.query(InfoLoTransactionBoot).filter(InfoLoTransactionBoot.id == datas.id, InfoLoTransactionBoot.type == 'RUNNING').update({"type": "CLOSE"})
                db.commit()
            return results
        raise HTTPException(status_code=403, detail="Không tìm thấy cặp tiền cần đóng")
    except Exception as e:
        db.rollback()
        print(f"Lỗi ở close_send: {e}")
    finally:
        db.close()

def get_close_order_boot(data, id):
    db = SessionLocal()
    try:
        offset = (data['page'] - 1) * data['limit']

        query = db.query(InfoLoTransactionBoot)

        # Danh sách các điều kiện động
        filters = [InfoLoTransactionBoot.login_id == id]

        if data['start_time'] is not None:
            start_dt = datetime.fromtimestamp(int(data['start_time']) / 1000)
            filters.append(InfoLoTransactionBoot.time >= start_dt)

        if data['end_time'] is not None:
            end_dt = datetime.fromtimestamp(int(data['end_time']) / 1000)
            filters.append(InfoLoTransactionBoot.time <= end_dt)
            

        total = db.query(func.count(InfoLoTransactionBoot.id)).filter(*filters).scalar()

        query = (
            db.query(OrdersBoot, InfoLoTransactionBoot)
            .join(InfoLoTransactionBoot, OrdersBoot.lo_boot_id == InfoLoTransactionBoot.id)
            .filter(*filters)
            .order_by(InfoLoTransactionBoot.time.desc())
            .offset(offset)
            .limit(data["limit"])
        )
        grouped_data = {}

        for order, info in query.all():
            info_id = info.id

            # Nếu info này chưa có trong grouped_data thì thêm vào
            if info_id not in grouped_data:
                info_dict = info.__dict__.copy()
                info_dict.pop("_sa_instance_state", None)
                info_dict["dataOrder"] = []  # danh sách chứa các order
                grouped_data[info_id] = info_dict

            # Thêm order vào danh sách
            order_dict = order.__dict__.copy()
            order_dict.pop("_sa_instance_state", None)
            grouped_data[info_id]["dataOrder"].append(order_dict)
            
        results = list(grouped_data.values())

        return {
            "total": total,
            "page": data['page'],
            "limit": data['limit'],
            "data": results
        }
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def get_detail_order_boot(id_info, id):
    db = SessionLocal()
    try:
        # Danh sách các điều kiện động
        filters = [InfoLoTransactionBoot.login_id == id, InfoLoTransactionBoot.id == id_info]

        query = (
            db.query(OrdersBoot, InfoLoTransactionBoot)
            .join(InfoLoTransactionBoot, OrdersBoot.lo_boot_id == InfoLoTransactionBoot.id)
            .filter(*filters)
            .order_by(InfoLoTransactionBoot.time.desc())
        )

        result = query.all()

        if not result:
            return {"message": "No data found"}

        # Dùng dict tạm để gom các order theo id_info
        grouped_data = {}

        for order, info in result:
            info_id = info.id

            # Nếu info này chưa có trong grouped_data thì thêm vào
            if info_id not in grouped_data:
                info_dict = info.__dict__.copy()
                info_dict.pop("_sa_instance_state", None)
                info_dict["dataOrder"] = []  # danh sách chứa các order
                grouped_data[info_id] = info_dict

            # Thêm order vào danh sách
            order_dict = order.__dict__.copy()
            order_dict.pop("_sa_instance_state", None)
            grouped_data[info_id]["dataOrder"].append(order_dict)

        # Trả ra danh sách các info (mỗi info có dataOrder là 1 list)
        data = list(grouped_data.values())

        return data
    except Exception as e:
        db.rollback()
        print("Lỗi đang xảy ra ở get_detail_order_boot: ", e)
    finally:
        db.close()