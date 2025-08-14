from src.models.modelTransaction.schemas import SymbolTransactionRequest
from src.models.modelTransaction.lot_information_model import LotInformation
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelTransaction.orders_transaction_model import OrdersTransaction
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.models.model import SessionLocal

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

def order_send_mt5(price: float, symbol: str, lot: float, order_type: str, usename_id: float, lot_id: float, account_transaction_id: float):
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

    print("Request order_send:", request)
    result = mt5.order_send(request)
    print("Result order_send:", result)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise Exception(f"Gửi lệnh thất bại: {result.retcode} - {result.comment}")
    else:
        ticket_id = result.order
        profit = get_floating_profit(result.order)
        symbol = SymbolTransaction(
            id_transaction= ticket_id,
            username_id = usename_id,
            lot_id = lot_id,
            account_transaction_id = account_transaction_id,
            symbol = symbol,
            price_transaction = price,
            volume = lot,
            type = order_type,
            digits = symbol_info.digits,
            contract_size = symbol_info.trade_contract_size,
            description= f"python-{symbol}",
            profit = profit,
            status = 'filled'
        )
        db.add(symbol)

        order_transaction = OrdersTransaction(
            id_transaction= ticket_id,
            account_id = account_transaction_id,
            symbol = symbol,
            order_type = order_type,
            volume = lot,
            price = price,
            sl = 0,
            tp = 0,
            status = 'filled'
        )
        db.add(order_transaction)

        db.commit()
        db.close()
        print("✅ Lệnh đã gửi:", result)
        return result
    
# Khởi tạo MT5 1 lần khi app start
def mt5_connect():
    if not mt5.initialize(path="C:/Program Files/MetaTrader 5/terminal64.exe"):
        raise Exception(f"MT5 chưa kết nối. Lỗi: {mt5.last_error()}")
    return True

# Hàm dùng trong thread, tạo session riêng
def run_order(order, data, username_id, lot_id):
    db = SessionLocal()
    try:
        message = order_send_mt5(
            price=order.current_price,
            symbol=order.symbol,
            lot=data.volume,
            order_type=order.type,
            usename_id=username_id,
            lot_id=lot_id,
            account_transaction_id=data.account_transaction_id
        )
        return {"symbol": order.symbol, "status": "success", "message": message}
    except Exception as e:
        db.rollback()
        return {"symbol": order.symbol, "status": "error", "message": str(e)}
    finally:
        db.close()

def place_market_lot(data: SymbolTransactionRequest, username_id):
    mt5_connect()  # đảm bảo MT5 đã connect 1 lần

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
        status_sl_tp=data.status_sl_tp
    )
    db.add(lotNew)
    db.commit()

    results = []
    if data.status == 'Lenh_thi_truong':
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(run_order, order, data, username_id, lotNew.id) for order in data.by_symbol]
            for future in as_completed(futures):
                results.append(future.result())
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
                volume = lotNew.id,
                price = by_symbol.current_price,
                sl = 0,
                tp = 0,
            )
            db.add(order_transaction)
        db.commit()
        db.close()
