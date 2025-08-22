import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import signal
from multiprocessing import Process, Queue, freeze_support,Event
from src.controls.transaction_controls.auto_order import transaction_account_order
from src.controls.transaction_controls.auto_position_transaction import auto_position
from src.services.terminals_transaction import terminals_transaction

def start_mt5_monitor():
    try:
        freeze_support()
        stop_event = Event()

        def handle_exit(signum, frame):
            print("🛑 Received signal — stopping all processes")
            stop_event.set()

        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)

        # Chạy tiến trình theo dõi PNL để vào lệnh và đóng lệnh
        processes = []
        for name, path in terminals_transaction.items():
            p1 = Process(target=transaction_account_order, args=(name, 1, stop_event))
            p1.start()
            processes.append(p1)

            p2 = Process(target=auto_position, args=(name, 1, stop_event))
            p2.start()
            processes.append(p2)

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