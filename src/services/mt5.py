import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from multiprocessing import Process, Queue, freeze_support
from src.controls.daily_email_sender import run_schedule_email
from src.controls.update_swap_mt5 import daily_swap_process
from src.routes.savePnl import logger_process, monitor_account

terminals = {
    "Acc1": "C:/Program Files/MetaTrader 5 - acc 1/terminal64.exe",
    "Acc2": "C:/Program Files/MetaTrader 5 - acc 2/terminal64.exe",
}

def start_mt5_monitor():
    freeze_support()
    queue = Queue()

    # Ghi dữ liệu vào file .xlsx, .csv
    log_proc = Process(target=logger_process, args=(queue,))
    log_proc.start()

    # Chạy tiến trình theo dõi PNL
    processes = []
    for name, path in terminals.items():
        p = Process(target=monitor_account, args=(path, name, 5, queue))
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

if __name__ == "__main__":
    start_mt5_monitor()