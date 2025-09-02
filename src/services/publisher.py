import time
import MetaTrader5 as mt5
from datetime import datetime, timedelta

# ================== PUBLISHER ==================
def tick_publisher(name, cfg, pub_queue, stop_event, monitor_queue):
    """
    Lấy tick từ tất cả terminals và symbols, push vào queue chung.
    """
    if not mt5.initialize(path=cfg["path"]):
        print(f"[{name}] ❌ Không khởi tạo được MT5 ở {cfg['path']}")
        return
    
    # Lấy tất cả position đang mở
    positions = mt5.positions_get()

    if positions is None:
        print("❌ Không có lệnh nào đang mở")
        symbols = []
    else:
        # Nếu positions là list of dict, lấy symbol đúng cách
        symbols = list({p.symbol for p in positions})  # dùng set để loại trùng

    # Khởi tạo last_time_map cho các symbol đang có lệnh mở
    last_time_map = {sym: None for sym in symbols}

    base_interval = 0.05  # interval mặc định
    min_interval = 0.01   # nhanh nhất
    max_interval = 0.2    # chậm nhất
    interval = base_interval
    idle_counter = 0

    # Monitor
    last_log_time = time.time()
    tick_count = 0

    while not stop_event.is_set():
        try:
            tick_received = False
            for symbol in symbols:
                try:
                    dt_from = datetime.now() - timedelta(seconds=5)
                    ticks = mt5.copy_ticks_from(symbol, dt_from, 50, mt5.COPY_TICKS_ALL)
                    if ticks is None or len(ticks) == 0:
                        continue

                    for tick in ticks:
                        if last_time_map[symbol] is None or tick['time'] > last_time_map[symbol]:
                            last_time_map[symbol] = tick['time']
                            tick_received = True
                            tick_count += 1
                            pub_queue.put((name, symbol, tick))
                except Exception as e:
                    print(f"[{name}] ❌ Error get tick {symbol}: {e}")

            
            # 🔄 Adaptive sleep
            if tick_received:
                idle_counter = 0
                interval = max(min_interval, interval * 0.7)  # nhanh hơn
            else:
                idle_counter += 1
                if idle_counter > 5:  # sau 5 vòng không tick mới
                    interval = min(max_interval, interval * 1.3)  # chậm lại

            # 📊 Monitor log mỗi 1s
            now = time.time()
            if now - last_log_time >= 1.0:
                monitor_queue.put((
                    "Publisher", "ALL",
                    {"ticks": tick_count, "queue": pub_queue.qsize(), "interval": interval}
                ))
                tick_count = 0
                last_log_time = now

            # thay time.sleep bằng stop_event.wait để có thể dừng ngay
            stop_event.wait(interval)
        except Exception as e:
            print(f"[Publisher] Error: {e}")
        time.sleep(interval)
    print("🛑 Tick publisher stopped.")


# ================== DISPATCHER ==================
def dispatcher(pub_queue, queues_map, pnl_queues_map, stop_event):
    """
    Nhận tick từ publisher, phân phát vào queue riêng theo terminal.
    """
    try:
        while not stop_event.is_set():
            try:
                item = pub_queue.get(timeout=0.5)
            except:
                continue

            if item is None:
                continue

            # Nếu là tuple => tick
            if isinstance(item, tuple) and len(item) == 3:
                name, symbol, tick = item
                if name in queues_map:
                    queues_map[name].put((symbol, tick))
                continue

            # Nếu là dict => phân loại theo type
            if isinstance(item, dict):
                src = item.get("source")
                typ = item.get("type")

                if typ == "pnl":
                    if src in pnl_queues_map:
                        pnl_queues_map[src].put(item)
                elif typ == "tick":
                    if src in queues_map:
                        queues_map[src].put(item)
                else:
                    print(f"[Dispatcher] ❓ Unknown type: {typ}")

    except Exception as e:
        print(f"[Dispatcher] Fatal error: {e}")
    finally:
        print("🛑 Dispatcher stopped.")

# ================== MONITOR ==================
def monitor(monitor_queue, stop_event):
    """
    Process monitor trung tâm, hiển thị số liệu từ Publisher + Workers.
    """
    stats = {}
    last_log_time = time.time()

    while not stop_event.is_set():
        try:
            # Nhận update từ Publisher/Worker
            role, name, data = monitor_queue.get(timeout=1)
            stats[(role, name)] = data
        except:
            pass

        # In log mỗi 1s
        now = time.time()
        if now - last_log_time >= 1.0:
            print("\n=================== SYSTEM MONITOR ===================")
            print(f"{'Role':<12} {'Name':<10} {'ticks/s':<10} {'queue':<8} {'interval':<10}")
            for (role, name), data in stats.items():
                ticks = data.get("ticks", 0)
                queue = data.get("queue", 0)
                interval = data.get("interval", 0)
                print(f"{role:<12} {name:<10} {ticks:<10} {queue:<8} {interval:<10.3f}")
            print("======================================================\n")

            # reset counters
            for k in stats:
                stats[k]["ticks"] = 0

            last_log_time = now
