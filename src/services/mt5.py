import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import signal
from multiprocessing import Process, Queue, freeze_support,Event
from src.controls.daily_email_sender import run_schedule_email
from src.controls.update_swap_mt5 import daily_swap_process
from src.routes.savePnl import logger_process, monitor_account

terminals = {
    "Acc1": "C:/Program Files/MetaTrader 5 - acc 1/terminal64.exe",
    "Acc2": "C:/Program Files/MetaTrader 5 - acc 2/terminal64.exe",
}

def start_mt5_monitor():
    try:
        freeze_support()
        queue = Queue()
        stop_event = Event()

        def handle_exit(signum, frame):
            print("🛑 Received signal — stopping all processes")
            stop_event.set()

        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)

        # Ghi dữ liệu vào file .xlsx, .csv
        log_proc = Process(target=logger_process, args=(queue, stop_event))
        log_proc.start()

        # Chạy tiến trình theo dõi PNL
        processes = []
        for name, path in terminals.items():
            p = Process(target=monitor_account, args=(path, name, 5, queue, stop_event))
            p.start()
            processes.append(p)

        # Update swap định kỳ 4h02 hằng ngày
        swap_proc = Process(target=daily_swap_process, args=(terminals,))
        swap_proc.start()
        processes.append(swap_proc)

        # Gửi email định kỳ 7h hằng ngày
        email_proc = Process(target=run_schedule_email)
        email_proc.start()
        processes.append(email_proc)
        
        for p in processes:
            p.join()
            
        log_proc.join()
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