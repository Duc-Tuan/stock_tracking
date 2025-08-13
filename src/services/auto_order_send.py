import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import signal
from multiprocessing import Process, Queue, freeze_support,Event
from src.controls.transaction_controls.auto_order import transaction_account_order

terminals = {
    "Acc1": "C:/Program Files/MetaTrader 5/terminal64.exe",
}

def start_mt5_monitor():
    try:
        freeze_support()
        stop_event = Event()

        def handle_exit(signum, frame):
            print("🛑 Received signal — stopping all processes")
            stop_event.set()

        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)

        # Chạy tiến trình theo dõi PNL
        processes = []
        for name, path in terminals.items():
            p = Process(target=transaction_account_order, args=(path, name, 1, stop_event))
            p.start()
            processes.append(p)

        for p in processes:
            p.join()
            
    except KeyboardInterrupt:
        print("\n🛑 Nhận Ctrl+C – Đang dừng các tiến trình con...")
    finally:
        for p in processes:
            if p.is_alive():
                p.terminate()
        print("✅ Dừng toàn bộ tiến trình thành công.")

    


if __name__ == "__main__":
    try:
        start_mt5_monitor()
    except KeyboardInterrupt:
        print("\n🛑 Đã nhận Ctrl+C – Đang dừng các tiến trình...")
        # Tuỳ chọn: gửi tín hiệu dừng về stop_flag, terminate process, cleanup
        sys.exit(0)