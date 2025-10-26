from src.models.modelTransaction.schemas import SymbolTransactionRequest, PatchotRequest
from src.models.modelTransaction.lot_information_model import LotInformation
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelTransaction.orders_transaction_model import OrdersTransaction
from src.models.modelTransaction.position_transaction_model import PositionTransaction
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.models.model import SessionLocal
from sqlalchemy import func
from datetime import datetime
from src.services.terminals_transaction import terminals_transaction
import re

from MetaTrader5 import (
    ORDER_TYPE_BUY, ORDER_TYPE_SELL,
    ORDER_FILLING_IOC, ORDER_TIME_GTC,
    TRADE_ACTION_DEAL, TRADE_ACTION_PENDING
)
import MetaTrader5 as mt5

def get_floating_profit(ticket_id):
    positions = mt5.positions_get(ticket=ticket_id)
    if positions:
        return positions[0].profit
    return None

# bỏ hậu tố
def replace_suffix_with_m(sym: str) -> str:
    # Lấy phần chữ cái và số chính (base symbol)
    base = re.match(r"[A-Z]{6}", sym.upper())
    if base:
        return base.group(0) + "m"
    else:
        # Nếu không match (trường hợp đặc biệt) thì fallback
        return sym.rstrip("cm") + "m"
    
def replace_suffix_with(sym: str) -> str:
    # Lấy phần chữ cái và số chính (base symbol)
    base = re.match(r"[A-Z]{6}", sym.upper())
    if base:
        return base.group(0)
    else:
        # Nếu không match (trường hợp đặc biệt) thì fallback
        return sym.rstrip("cm")

def isCheckServerAccTransac(usname: int) -> str:
    return terminals_transaction[str(usname)]["server"]

def order_send_mt5(is_odd: bool | None, price: float | None, symbol: str, lot: float, order_type: str, usename_id: float, lot_id: float, account_transaction_id: float):
    symbol_replace = replace_suffix_with_m(symbol)

    # if "Exness" in isCheckServerAccTransac(account_transaction_id):
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
        "magic": 123456,
        "comment": f"python-{symbol}",
        "type_time": ORDER_TIME_GTC,
    }

    if "Exness" in isCheckServerAccTransac(account_transaction_id):
        request["type_filling"] = ORDER_FILLING_IOC

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise Exception(f"Gửi lệnh thất bại: {result.retcode} - {result.comment}")
    else:
        ticket_id = result.order
        profit = get_floating_profit(result.order)
        is_odd_value = True if is_odd else False
        symbolSQL = SymbolTransaction(
            id_transaction= ticket_id,
            username_id = usename_id,
            lot_id = lot_id,
            account_transaction_id = account_transaction_id,
            symbol = symbol_replace,
            price_transaction = price,
            volume = lot,
            type = order_type,
            digits = symbol_info.digits,
            contract_size = symbol_info.trade_contract_size,
            description= f"python-{symbol}",
            profit = profit,
            status = 'filled',
            is_odd = is_odd_value
        )
        order_transaction = OrdersTransaction(
            id_transaction= ticket_id,
            account_id = account_transaction_id,
            symbol = symbol_replace,
            order_type = order_type,
            volume = lot,
            price = price,
            sl = 0,
            tp = 0,
            status = 'filled',
            profit = profit,
        )
        print("✅ Lệnh đã gửi:", result)
        return {"result": result, "status": "success", "data": (symbolSQL, order_transaction)}
    
# Khởi tạo MT5 1 lần khi app start
def mt5_connect(account_name: int):
    acc = terminals_transaction[str(account_name)]
    # Đóng kết nối cũ nếu đang mở
    mt5.shutdown()
    # Kết nối mới
    if not mt5.initialize(path=acc["path"], login=acc["login"], password=acc["password"], server=acc["server"]):
        raise Exception(f"Không connect được MT5 {account_name}. Lỗi: {mt5.last_error()}")
    return True

# Hàm dùng trong thread, tạo session riêng
def run_order(order, data, username_id, lot_id):
    try:
        message = order_send_mt5(
            is_odd = False,
            price=order.current_price,
            symbol=order.symbol,
            lot=data.volume,
            order_type=order.type,
            usename_id=username_id,
            lot_id=lot_id,
            account_transaction_id=data.account_transaction_id
        )
        return {"symbol": order.symbol, "status": "success", "message": message, "data": message["data"]}
    except Exception as e:
        return {"symbol": order.symbol, "status": "error", "message": str(e)}

def place_market_lot(data: SymbolTransactionRequest, username_id):
    mt5_connect(data.account_transaction_id)  # đảm bảo MT5 đã connect 1 lần

    db = SessionLocal()

    lotNew = LotInformation(
        username_id=username_id,
        account_monitor_id=data.account_monitor_id,
        account_transaction_id=data.account_transaction_id,
        price=data.price,
        volume=data.volume,
        stop_loss=data.stop_loss,
        take_profit=data.take_profit,
        status=data.status,
        type=data.type,
        status_sl_tp=data.status_sl_tp,
        IsUSD=data.IsUSD,
        usd=data.usd
    )
    db.add(lotNew)
    db.flush()

    if data.status == 'Lenh_thi_truong':
        results = []
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(run_order, order, data, username_id, lotNew.id) for order in data.by_symbol]
            for future in as_completed(futures):
                results.append(future.result())

            try:
                # ✅ chỉ commit khi tất cả run_order return success
                if all(r["status"] == "success" for r in results):
                    for r in results:
                        symbolSQL, order_transaction = r["data"]
                        db.add(symbolSQL)
                        db.add(order_transaction)
                    db.commit()
                else:
                    db.rollback()
            finally:
                db.close()
        return results
    else:
        for by_symbol in data.by_symbol:
            symbol = SymbolTransaction(
                username_id=username_id,
                lot_id=lotNew.id,
                account_transaction_id=data.account_transaction_id,
                symbol=by_symbol.symbol,
                price_transaction=by_symbol.current_price,
                volume=data.volume,
                type=by_symbol.type,
                digits=0
            )
            db.add(symbol)
            order_transaction = OrdersTransaction(
                account_id = data.account_transaction_id,
                symbol = by_symbol.symbol,
                order_type = by_symbol.type,
                volume = data.volume,
                price = by_symbol.current_price,
                sl = 0,
                tp = 0,
            )
            db.add(order_transaction)
        db.commit()
        db.close()

def get_symbols_lot(id_lot, id_user):
    db = SessionLocal()
    try:
        rows = db.query(
            SymbolTransaction.symbol,
            SymbolTransaction.price_transaction,
            SymbolTransaction.type).filter(SymbolTransaction.username_id == id_user, SymbolTransaction.lot_id == id_lot).order_by(SymbolTransaction.time.desc()).all()
        
        return [
            {
                "symbol": symbol,
                "price_transaction": price_transaction,
                "type": type
            }
            for symbol, price_transaction, type in rows
        ]
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def get_symbols_db(data, id_user):
    db = SessionLocal()
    try:
        offset = (data['page'] - 1) * data['limit']

        query = db.query(LotInformation)

        # Danh sách các điều kiện động
        filters = [LotInformation.username_id == id_user]

        if data['status'] is not None:
            filters.append(LotInformation.status == data['status'])

        if data['statusType'] is not None:
            filters.append(LotInformation.type == data['statusType'])

        if data['acc_transaction'] is not None:
            filters.append(LotInformation.account_transaction_id == int(data['acc_transaction']))

        if data['start_time'] is not None:
            start_dt = datetime.fromtimestamp(int(data['start_time']) / 1000)
            filters.append(LotInformation.time >= start_dt)

        if data['end_time'] is not None:
            end_dt = datetime.fromtimestamp(int(data['end_time']) / 1000)
            filters.append(LotInformation.time <= end_dt)
            

        total = db.query(func.count(LotInformation.id)).filter(*filters).scalar()

        dataLots = (
            query.filter(*filters)
            .order_by(LotInformation.time.desc())
            .offset(offset)
            .limit(data['limit'])
            .all()
        )

        

        # 🔹 Chuyển sang list dict và thêm trường mới
        result_data = []
        for item in dataLots:
            item_dict = item.__dict__.copy()
            item_dict.pop("_sa_instance_state", None)  # bỏ metadata SQLAlchemy
            # Ví dụ: thêm trường mới
            item_dict["bySymbol"] = get_symbols_lot(item.id, id_user)
            result_data.append(item_dict)

        return {
            "total": total,
            "page": data['page'],
            "limit": data['limit'],
            "data": result_data
        }
    except Exception as e:
        db.rollback()
        print("Lỗi trong hàm get_symbols_db: ", e)
    finally:
        db.close()

def delete_lot_transaction(id: int):
    db = SessionLocal()
    try: 
        lot = db.query(LotInformation).filter(
            LotInformation.id == id, 
            LotInformation.type == "RUNNING",
            LotInformation.status.in_(["Xuoi_Limit", "Nguoc_Limit", "Xuoi_Stop", "Nguoc_Stop"])
        ).first()

        if lot:
            db.delete(lot)
            db.query(SymbolTransaction).filter(SymbolTransaction.lot_id == lot.id).delete()
            db.commit()
            return {"status": "success", "message": "Xóa thành công."}

        return {"status": "error", "message": "Không tìm thấy thông tin lô cần xóa."}
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi trong đóng lệnh nhanh: {e}")
    finally:
        db.close()

def patch_lot_transaction(data: PatchotRequest):
    db = SessionLocal()
    try: 
        lot = db.query(LotInformation).filter(
            LotInformation.id == data.id, 
            LotInformation.type == "RUNNING",
            LotInformation.status == "Lenh_thi_truong"
        ).first()


        if lot:
            db.query(LotInformation).filter( 
                LotInformation.id == data.id, 
                LotInformation.type == "RUNNING",
                LotInformation.status == "Lenh_thi_truong"
            ).update({
                "stop_loss": float(data.stop_loss),
                "take_profit": float(data.take_profit)
            })

            db.commit()
            return {"status": "success", "message": "Update thành công"}

        return {"status": "error", "message": "Không tìm thấy thông tin lô cần update."}
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi trong đóng lệnh nhanh: {e}")
    finally:
        db.close()


def close_position_transaction_controll(ticket: int, volume: float, loginId: int, acc_transaction: int):
    try: 
        db = SessionLocal()

        deviation = 30
        
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return {"error": f"Không tìm thấy lệnh với ticket {ticket}"}

        pos = position[0]

        # Nếu volume yêu cầu lớn hơn volume hiện tại thì giới hạn lại
        if volume > pos.volume:
            volume = pos.volume

        # Xác định loại lệnh đóng (ngược lại)
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY

        # Lấy giá hiện tại
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            return {"error": f"Không lấy được giá cho {pos.symbol}"}

        price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask

        # Tạo request đóng lệnh với volume yêu cầu
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": volume,   # 🔥 chỉ đóng 1 phần
            "type": close_type,
            "position": pos.ticket,
            "price": price,
            "deviation": deviation,
            "magic": pos.magic,
            "comment": f"Close{volume}_{pos.ticket}"[:30],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise Exception(f"Gửi lệnh thất bại: {result.retcode} - {result.comment}")
        else:
            isCheck = db.query(PositionTransaction).filter(PositionTransaction.id_transaction == ticket).first()
            if(isCheck):
                if (float(isCheck.volume) <= float(volume)):
                    db.query(SymbolTransaction).filter(SymbolTransaction.id_transaction == ticket).update({"status": "cancelled"})
                    db.query(OrdersTransaction).filter(OrdersTransaction.id_transaction == ticket).update({"status": "cancelled"})
                    db.query(PositionTransaction).filter(PositionTransaction.id_transaction == ticket).delete()
                else:
                    db.query(PositionTransaction).filter(PositionTransaction.id_transaction == ticket).update({"profit": pos.profit,"volume": float(isCheck.volume) - float(volume)})

            db.commit()
        return {"success": f"Cắt {volume}/{isCheck.volume} của cặp tiền {pos.symbol} thành công"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close