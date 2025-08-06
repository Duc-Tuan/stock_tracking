from MetaTrader5 import (
    ORDER_TYPE_BUY, ORDER_TYPE_SELL,
    ORDER_TYPE_BUY_LIMIT, ORDER_TYPE_SELL_LIMIT,
    ORDER_TYPE_BUY_STOP, ORDER_TYPE_SELL_STOP,
    ORDER_FILLING_IOC, ORDER_TIME_GTC,
    TRADE_ACTION_DEAL, TRADE_ACTION_PENDING
)
import MetaTrader5 as mt5

def place_market_order(symbol: str, lot: float, slippage: int, order_type: str):
    if not mt5.initialize(path="C:/Program Files/MetaTrader 5/terminal64.exe"):
        raise Exception(f"MT5 chưa kết nối. Lỗi: {mt5.last_error()}")

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        raise Exception(f"Không tìm thấy symbol: {symbol}")

    if not symbol_info.visible:
        mt5.symbol_select(symbol, True)

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise Exception(f"Không lấy được giá cho symbol: {symbol}")

    ask = tick.ask
    bid = tick.bid

    # Chuyển order_type từ chuỗi sang mã lệnh MT5
    order_type_map = {
        "buy": ORDER_TYPE_BUY,
        "sell": ORDER_TYPE_SELL,
        "buy_limit": ORDER_TYPE_BUY_LIMIT,
        "sell_limit": ORDER_TYPE_SELL_LIMIT,
        "buy_stop": ORDER_TYPE_BUY_STOP,
        "sell_stop": ORDER_TYPE_SELL_STOP,
    }

    if order_type not in order_type_map:
        raise Exception(f"Loại lệnh không hợp lệ: {order_type}")

    mt5_order_type = order_type_map[order_type]

    # Xác định giá gửi lệnh phù hợp
    if "buy" in order_type:
        price = ask
    else:
        price = bid

    # Nếu là lệnh chờ → TRADE_ACTION_PENDING, còn lại là DEAL
    action_type = TRADE_ACTION_DEAL if order_type in ["buy", "sell"] else TRADE_ACTION_PENDING

    request = {
        "action": action_type,
        "symbol": symbol,
        "volume": lot,
        "type": mt5_order_type,
        "price": price,
        "slippage": slippage,
        "magic": 123456,
        "comment": f"python-{order_type}",
        "type_time": ORDER_TIME_GTC,
        "type_filling": ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise Exception(f"Gửi lệnh thất bại: {result.retcode} - {result.comment}")
    else:
        print("✅ Lệnh đã gửi:", result)
        return result

