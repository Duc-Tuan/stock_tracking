import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import signal
import time
from multiprocessing import Process, Queue, freeze_support, Event, Manager
from src.routes.savePnl import monitor_account
from src.services.publisher import monitor, tick_publisher, dispatcher
from src.controls.transaction_controls.auto_order import auto_send_order_acc_transaction
from src.controls.update_swap_mt5 import daily_swap_process

terminals = {
    "263006287": {
        "path": "C:/Program Files/MetaTrader 5 - acc 1/terminal64.exe",
    },
    "183459647": {
        "path": "C:/Program Files/MetaTrader 5 - acc 2/terminal64.exe",
    }
}

def start_mt5_monitor():
    freeze_support()
    stop_event = Event()
    pub_queue = Queue()
    monitor_queue = Queue()
    processes = []

    # Quản lý queue riêng cho từng terminal
    manager = Manager()
    queues_map = {name: manager.Queue() for name in terminals.keys()}   # cho tick
    pnl_queues_map = {name: manager.Queue() for name in terminals.keys()}   # cho PnL

    def handle_exit(signum, frame):
        print("🛑 Nhận tín hiệu dừng – stop tất cả tiến trình")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # Monitor process
    mon = Process(target=monitor, args=(monitor_queue, stop_event))
    mon.start()
    processes.append(mon)

    # Dispatcher
    disp = Process(target=dispatcher, args=(pub_queue, queues_map, pnl_queues_map, stop_event))
    disp.start()
    processes.append(disp)

    dailay_swap = Process(target=daily_swap_process, args=(terminals,))
    dailay_swap.start()
    processes.append(dailay_swap)

    # Chạy tiến trình theo dõi PNL
    for name, cfg in terminals.items():
        # Publisher
        publisher = Process(target=tick_publisher, args=(name, cfg, pub_queue, stop_event, monitor_queue))
        publisher.start()
        processes.append(publisher)

        q = queues_map[name]
        pnl_q = pnl_queues_map[name] 

        p = Process(target=monitor_account, args=(name, cfg, q, stop_event, pub_queue))
        p.start()
        processes.append(p)

        p1 = Process(target=auto_send_order_acc_transaction, args=(pnl_q, stop_event))
        p1.start()
        processes.append(p1)

    try:
        # chờ các process kết thúc (nếu Ctrl+C -> handle_exit sẽ set stop_event)
        for p in processes:
            # join nhỏ để có thể bắt KeyboardInterrupt ở parent
            while p.is_alive():
                p.join(timeout=0.5)
    except KeyboardInterrupt:
        print("\n🛑 Nhận Ctrl+C – Đang dừng các tiến trình con...")
        stop_event.set()
    finally:
        print("🛑 Đang gửi tín hiệu dừng tới tất cả tiến trình...")
        stop_event.set()
        # cho các child thời gian thoát sạch
        for _ in range(10):
            alive = [p for p in processes if p.is_alive()]
            if not alive:
                break
            time.sleep(0.2)
        # nếu vẫn còn tiến trình sống -> terminate mạnh
        for p in processes:
            if p.is_alive():
                print(f"🔪 Terminating {p.name} (pid={p.pid})")
                p.terminate()
        for p in processes:
            p.join(timeout=1)
        print("✅ Dừng toàn bộ tiến trình thành công.")

if __name__ == "__main__":
    try:
        start_mt5_monitor()
    except KeyboardInterrupt:
        print("\n🛑 Đã nhận Ctrl+C – Đang dừng các tiến trình...")
        sys.exit(0)