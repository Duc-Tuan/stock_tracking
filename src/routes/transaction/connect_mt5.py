import MetaTrader5 as mt5

# Kết nối tới terminal
def connect_to_mt5():
    if not mt5.initialize(path="C:/Program Files/MetaTrader 5/terminal64.exe"):
        raise Exception(f"Kết nối thất bại. Lỗi: {mt5.last_error()}")
    else:
        print("✅ Đã kết nối với MT5 Terminal.")

def shutdown_mt5():
    mt5.shutdown()
