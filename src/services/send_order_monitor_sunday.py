from datetime import datetime
import time
import MetaTrader5 as mt5

def connect_mt5(path):
    """Kết nối MT5 với terminal cụ thể"""
    if not mt5.initialize(path):
        print(f"❌ Lỗi kết nối MT5 ({path}): {mt5.last_error()}")
        return False
    return True

def disconnect_mt5():
    """Ngắt kết nối MT5"""
    mt5.shutdown()

def auto_send_btc_order(name, cfg, symbol="BTCUSDm", volume=0.01):
    """Vào 1 lệnh BUY BTC"""
    if not connect_mt5(cfg["path"]):
        return None

    # Chọn symbol nếu chưa được add vào Market Watch
    if not mt5.symbol_select(symbol, True):
        print(f"❌ Terminal {name}: Không thể chọn symbol {symbol}")
        disconnect_mt5()
        return None

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"❌ Terminal {name}: Không lấy được giá {symbol}")
        disconnect_mt5()
        return None

    price = tick.ask
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "deviation": 10,
        "magic": 123456,
        "comment": f"Sunday BTC trade {name}",
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Terminal {name}: Lỗi vào lệnh BTC, retcode={result.retcode}")
        disconnect_mt5()
        return None

    print(f"✅ Terminal {name}: Vào lệnh BTC thành công, ticket {result.order}")
    disconnect_mt5()
    return result.order

def auto_close_order(name, cfg, ticket):
    """Đóng lệnh BTC theo ticket"""
    if ticket is None:
        print(f"❌ Terminal {name}: Không có ticket để đóng")
        return

    if not connect_mt5(cfg["path"]):
        return

    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        print(f"❌ Terminal {name}: Không tìm thấy lệnh ticket {ticket}")
        disconnect_mt5()
        return

    position = positions[0]
    symbol = position.symbol
    volume = position.volume

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"❌ Terminal {name}: Không lấy được giá đóng {symbol}")
        disconnect_mt5()
        return

    price = tick.bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_SELL,
        "position": ticket,
        "price": price,
        "deviation": 10,
        "magic": 123456,
        "comment": f"Sunday BTC close {name}",
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Terminal {name}: Lỗi đóng lệnh BTC, retcode={result.retcode}")
    else:
        print(f"✅ Terminal {name}: Đóng lệnh BTC ticket {ticket}")
    disconnect_mt5()

def sunday_btc_trade(terminals, stop_event):
    traded_this_sunday = False

    while not stop_event.is_set():
        now = datetime.now()
        if now.weekday() == 6:  # Chủ Nhật
            if not traded_this_sunday:
                print("🚀 Chủ Nhật - Thực hiện BTC trade cho tất cả terminal")
                for name, cfg in terminals.items():
                    try:
                        ticket = auto_send_btc_order(name, cfg, symbol="BTCUSDm", volume=0.01)
                        auto_close_order(name, cfg, ticket)
                    except Exception as e:
                        print(f"❌ Terminal {name}: Lỗi trade BTC: {e}")
                traded_this_sunday = True  # đánh dấu đã trade tuần này
        else:
            traded_this_sunday = False  # reset cờ khi không phải CN

        time.sleep(10)  # check lại mỗi 30 giây
