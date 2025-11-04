import MetaTrader5 as mt5
import re
from typing import List
from datetime import datetime
from sqlalchemy import func
from fastapi import HTTPException
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.models.model import SessionLocal
from src.models.modelTransaction.schemas import SendOrderBootMonitorRequest, dataSendOrderBootMonitorRequest, CloseOrderBoot
from src.services.terminals_transaction import terminals_transaction
from src.models.modelBootAccMonitor.info_boot_monitor_model import InfoBootMonitorBoot
from src.models.modelBootAccMonitor.symbol_boot_monitor_model import SymbolMonitorBoot
from src.models.modelBootAccMonitor.position_boot_monitor_model import PositionMonitorBoot


from MetaTrader5 import (
    ORDER_TYPE_BUY, ORDER_TYPE_SELL,
    ORDER_FILLING_IOC, ORDER_TIME_GTC,
    TRADE_ACTION_DEAL, TRADE_ACTION_PENDING
)

def isCheckServerAccTransac(usname: int) -> str:
    return terminals_transaction[str(usname)]["server"]

# ------------------------------
# Kết nối MT5 cho tài khoản cụ thể
# ------------------------------
def mt5_connect(account_name: int):
    acc = terminals_transaction[str(account_name)]
    mt5.shutdown()
    if not mt5.initialize(path=acc["path"], login=acc["login"], password=acc["password"], server=acc["server"]):
        raise Exception(f"Không connect được MT5 {account_name}. Lỗi: {mt5.last_error()}")
    return True

# ------------------------------
# Chạy đa luồng gửi lệnh
# ------------------------------
def replThreadPoolExecutor(db, lotNew, datas: List[dataSendOrderBootMonitorRequest], volume: float, acc: int, username_id: int):
    mt5_connect(acc)
    results = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_order, lotNew, data, volume, acc, username_id) for data in datas]
        for future in as_completed(futures):
            results.append(future.result())
    return results


# ------------------------------
# Đặt lot market song song cho 2 tài khoản
# ------------------------------
def place_market_lot(data: List[SendOrderBootMonitorRequest], username_id):
    db = SessionLocal()

    exness_orders = next(o for o in data if o.type == 'EXNESS')
    fund_orders = next(o for o in data if o.type == 'FUND')

    lotNew = InfoBootMonitorBoot(
        login_id=username_id,
        acc_reference=exness_orders.username,
        acc_reciprocal=fund_orders.username,
        type_acc_reference=exness_orders.type_acc,
        type_acc_reciprocal=fund_orders.type_acc,
        type="RUNNING",
        tp_acc_reference=exness_orders.tp,
        tp_acc_reciprocal=fund_orders.tp,
        volume=exness_orders.volume,
        acc_monitor=exness_orders.acc_monitor,
    )
    db.add(lotNew)
    db.flush()

    results = []

    if exness_orders and fund_orders:
        result1 = replThreadPoolExecutor(db, lotNew, exness_orders.data, exness_orders.volume, exness_orders.username, username_id)
        result2 = replThreadPoolExecutor(db, lotNew, fund_orders.data, fund_orders.volume, fund_orders.username, username_id)
        results = result1 + result2  # ✅ flatten list

    try:
        if all(r["status"] == "success" for r in results):
            for r in results:
                symbolSQL = r["data"]
                db.add(symbolSQL)
                db.commit()
    except Exception as e:
        db.rollback()
        print(f"Lỗi ở place_market_lot: {e}")
    finally:
        db.close()

    return results

# ------------------------------
# Xử lý symbol suffix (.r, .m, .c)
# ------------------------------
def replace_suffix_with(sym: str) -> str:
    base = re.match(r"[A-Z]{6}", sym.upper())
    if base:
        return base.group(0) + "m"
    else:
        # Nếu không match (trường hợp đặc biệt) thì fallback
        return sym.rstrip("cm") + "m"


def get_floating_profit(ticket_id):
    positions = mt5.positions_get(ticket=ticket_id)
    return positions[0].profit if positions else None


# ------------------------------
# Hàm thực hiện gửi lệnh MT5
# ------------------------------
def run_order(lotNew, data: dataSendOrderBootMonitorRequest, volume: float, acc: int, username_id: int):
    try:
        symbol = data.symbol
        type = data.type

        symbol_replace = replace_suffix_with(symbol)
        symbol_info = mt5.symbol_info(symbol_replace)
        if symbol_info is None:
            return {"status": "failed", "error": f"Không tìm thấy symbol: {symbol_replace}"}

        tick = mt5.symbol_info_tick(symbol_replace)
        if tick is None:
            return {"status": "failed", "error": f"Không lấy được giá cho symbol: {symbol_replace}"}

        order_type_map = {"BUY": ORDER_TYPE_BUY, "SELL": ORDER_TYPE_SELL}
        if type not in order_type_map:
            return {"status": "failed", "error": f"Loại lệnh không hợp lệ: {type}"}

        mt5_order_type = order_type_map[type]
        price = tick.ask if type == "BUY" else tick.bid

        request = {
            "action": TRADE_ACTION_DEAL,
            "symbol": symbol_replace,
            "volume": volume,
            "type": mt5_order_type,
            "price": price,
            "slippage": 0,
            "magic": 123456,
            "comment": f"boot_monitor-{symbol}",
            "type_time": ORDER_TIME_GTC,
            "type_filling": ORDER_FILLING_IOC,
        }

        if "Exness" in isCheckServerAccTransac(acc):
            request["type_filling"] = ORDER_FILLING_IOC

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"status": "failed", "error": f"{result.retcode} - {result.comment}"}

        ticket_id = result.order
        profit = get_floating_profit(ticket_id)

        symbolSQL = SymbolMonitorBoot(
            id_transaction=ticket_id,
            username_id=username_id,
            lot_id=lotNew.id,
            account_transaction_id=acc,
            symbol=symbol_replace,
            price_open=price,
            volume=volume,
            type=type,
            digits=symbol_info.digits,
            contract_size=symbol_info.trade_contract_size,
            description=f"python-{symbol}",
            profit=profit,
            status='filled',
        )

        return {"status": "success", "data": symbolSQL}

    except Exception as e:
        # ✅ Không để Exception object lọt ra ngoài
        return {"status": "failed", "error": str(e)}

def get_order_monitor_boot(data, id_user):
    db = SessionLocal()
    try:
        offset = (data['page'] - 1) * data['limit']

        # ------------------------------
        # 1️⃣ Lọc InfoBootMonitorBoot theo điều kiện
        # ------------------------------
        filters = [InfoBootMonitorBoot.login_id == id_user]

        if data.get('start_time'):
            start_dt = datetime.fromtimestamp(int(data['start_time']) / 1000)
            filters.append(InfoBootMonitorBoot.time >= start_dt)

        if data.get('end_time'):
            end_dt = datetime.fromtimestamp(int(data['end_time']) / 1000)
            filters.append(InfoBootMonitorBoot.time <= end_dt)

        total = db.query(func.count(InfoBootMonitorBoot.id)).filter(*filters).scalar()

        # Bước 1: lấy các ID InfoBootMonitorBoot theo trang
        subquery = (
            db.query(InfoBootMonitorBoot.id)
            .filter(*filters)
            .order_by(InfoBootMonitorBoot.time.desc())
            .offset(offset)
            .limit(data["limit"])
            .subquery()
        )

        # ------------------------------
        # 2️⃣ Join để lấy đầy đủ dữ liệu con
        # ------------------------------
        query = (
            db.query(SymbolMonitorBoot, InfoBootMonitorBoot)
            .join(InfoBootMonitorBoot, SymbolMonitorBoot.lot_id == InfoBootMonitorBoot.id)
            .filter(InfoBootMonitorBoot.id.in_(subquery))
            .order_by(InfoBootMonitorBoot.time.desc())
        )

        existing = query.all()

        # ------------------------------
        # 3️⃣ Gom nhóm dữ liệu
        # ------------------------------
        result = {}
        for symbol, info in existing:
            info_id = info.id

            if info_id not in result:
                info_dict = info.__dict__.copy()
                info_dict.pop("_sa_instance_state", None)
                info_dict["dataOrder"] = []
                result[info_id] = info_dict

            symbol_dict = symbol.__dict__.copy()
            symbol_dict.pop("_sa_instance_state", None)
            result[info_id]["dataOrder"].append(symbol_dict)

        result_list = list(result.values())

        return {
            "total": total,
            "page": data['page'],
            "limit": data['limit'],
            "data": result_list
        }

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_detail_order_boot(id, id_user):
    db = SessionLocal()
    try:
        # Danh sách các điều kiện động
        filters = [InfoBootMonitorBoot.login_id == id_user, InfoBootMonitorBoot.id == id]

        query = (
            db.query(SymbolMonitorBoot, InfoBootMonitorBoot)
            .join(InfoBootMonitorBoot, SymbolMonitorBoot.lot_id == InfoBootMonitorBoot.id)
            .filter(*filters)
            .order_by(InfoBootMonitorBoot.time.desc())
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


def close_order_boot(data: CloseOrderBoot, id_user: int):
    try:
        db = SessionLocal()
        isCheck = db.query(InfoBootMonitorBoot).filter(InfoBootMonitorBoot.id == data.id, InfoBootMonitorBoot.login_id == id_user, InfoBootMonitorBoot.type == 'RUNNING').first()

        if (isCheck):
            orderBoots = db.query(SymbolMonitorBoot).filter(SymbolMonitorBoot.lot_id == isCheck.id, SymbolMonitorBoot.status == 'filled').all()
            results = []
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(run_boot_close_order, orderBoot) for orderBoot in orderBoots]
                for future in as_completed(futures):
                    results.append(future.result())
            if (r and r.get("status") == "success" for r in results):
                db.query(InfoBootMonitorBoot).filter(InfoBootMonitorBoot.id == isCheck.id, InfoBootMonitorBoot.type == 'RUNNING').update({"type": "CLOSE"})
                db.commit()
            return results
        raise HTTPException(status_code=403, detail="Không tìm thấy cặp tiền cần đóng")
    except Exception as e:
        db.rollback()
        print(f"Lỗi ở close_send: {e}")
    finally:
        db.close()

def run_boot_close_order(data):
    mt5_connect(data.account_transaction_id)

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
            db.query(PositionMonitorBoot).filter(PositionMonitorBoot.id_transaction == ticket_id).delete(synchronize_session=False)
            db.query(SymbolMonitorBoot).filter(SymbolMonitorBoot.id_transaction == ticket_id).update({"status": "cancelled"})
            db.commit()

        return {"symbol": pos.volume, "status": "success", "message": result}
    except Exception as e:
        db.rollback()
        print(f"Lỗi ở close_send: {e}")
    finally:
        db.close()
