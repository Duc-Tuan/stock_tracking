import time
import json
import traceback
import MetaTrader5 as mt5
from datetime import datetime, date
import queue as pyqueue
from sqlalchemy.orm import Session
from sqlalchemy import func, text

# from src.models.modelMultiAccountPnL import MultiAccountPnL
from src.models.modelstatisticalPnl import StatisticalPNL
from src.models.model import SessionLocal
from src.models.modelAccMt5 import AccountMt5
from src.utils.stop import swap_difference
from src.services.socket_manager import emit_chat_message_sync
from src.services.save_pnl_aggregator import save_pnl_to_timeframes

from src.models.modelPNL import (
    MultiAccountPnL_D, MultiAccountPnL_W, MultiAccountPnL_MN,
)

def sqlalchemy_to_dict(row):
    d = row.__dict__.copy()
    d.pop("_sa_instance_state", None)
    for k, v in d.items():
        if isinstance(v, (datetime, date)):
            d[k] = v.isoformat()  # date cũng có isoformat() -> 'YYYY-MM-DD'
    return d


def monitor_account(name, cfg, queue, stop_event, pub_queue):
    if not mt5.initialize(path=cfg["path"]):
        print(f"[{name}] ❌ Không khởi tạo được MT5 ở {cfg['path']}")
        return
    session: Session = SessionLocal()

    # ✅ Thêm bộ đếm và thời gian để checkpoint WAL định kỳ
    checkpoint_counter = 0
    last_checkpoint_time = time.time()
    CHECKPOINT_INTERVAL = 300         # 300s = 5 phút
    CHECKPOINT_BATCH_COUNT = 300      # hoặc mỗi 300 vòng lặp, whichever comes first

    try: 
        while not stop_event.is_set():
            try:
                queue.get(timeout=1)
            except pyqueue.Empty:
                # không có tín hiệu mới → bỏ qua vòng lặp
                continue
            try:
                # === Lấy thông tin PnL từ MT5 ===
                account_info = mt5.account_info()
                should_save_today = datetime.today().weekday() != 6

                if account_info and should_save_today:
                    positions = mt5.positions_get()
                    if positions is None:
                        continue

                    total_pnl = 0.0
                    num_positions = 0
                    by_symbol = {}
                    symbols_acc_monitor = []

                    for pos in positions:
                        tick = mt5.symbol_info_tick(pos.symbol)

                        num_positions += 1
                        total_pnl += pos.profit
                        symbols_acc_monitor.append(pos.symbol)

                        if tick:
                            by_symbol[pos.symbol] = {
                                "current_price": tick.bid if pos.type == 0 else tick.ask,
                                "type": "BUY" if pos.type == 0 else "SELL",
                                "profit": pos.profit,
                            }

                    total_swap_difference = swap_difference(session, account_info)
                    total_pnl = account_info.profit + abs(total_swap_difference)

                    by_symbol_json = json.dumps(by_symbol)
                    by_symbol_json_acc_monitor = json.dumps(symbols_acc_monitor)

                    existing = session.query(AccountMt5).filter(AccountMt5.username == account_info.login).all()
                    if (len(existing) == 0):
                        new_data = AccountMt5(
                            username=account_info.login, 
                            password='', 
                            loginId=1, 
                            server=account_info.server, 
                            by_symbol=by_symbol_json_acc_monitor
                        )
                        session.add(new_data)

                    save_pnl_to_timeframes(
                        session=session,
                        login=account_info.login,
                        total_pnl=total_pnl
                    )

                    update_statistics(session, account_info.login, total_pnl)

                    session.commit()

                    statistical_login = (
                        session.query(StatisticalPNL)
                        .filter(StatisticalPNL.login == account_info.login)
                        .all()
                    )

                    result_statistical = [sqlalchemy_to_dict(row) for row in statistical_login]

                    data_send = {
                        "login": account_info.login,
                        "total_pnl": total_pnl,
                        "by_symbol": by_symbol_json,
                        "time": datetime.now().isoformat(),
                        "statistical": result_statistical
                    }

                    pub_queue.put({   # 👈 gửi vào pub_queue để dispatcher phân phát
                        "source": name,
                        "type": "pnl",
                        "data": data_send
                    })

                    # ✅ Checkpoint WAL định kỳ (ngăn file .wal phình)
                    checkpoint_counter += 1
                    now = time.time()
                    if checkpoint_counter >= CHECKPOINT_BATCH_COUNT or (now - last_checkpoint_time) > CHECKPOINT_INTERVAL:
                        try:
                            session.execute(text("PRAGMA wal_checkpoint(TRUNCATE);"))
                            print(f"[{name}] ✅ WAL checkpoint done ({datetime.now().strftime('%H:%M:%S')})")
                        except Exception as e:
                            print(f"[{name}] ⚠️ Lỗi khi checkpoint WAL: {e}")
                        checkpoint_counter = 0
                        last_checkpoint_time = now

            except Exception as e:
                session.rollback()
                print(f"❌ Lỗi trong monitor_account: {e}")
                traceback.print_exc()
                continue
            
            # ✅ luôn gửi socket, kể cả khi auto_send_order_acc_transaction bị lỗi
            try:
                if should_save_today:
                    emit_chat_message_sync("chat_message", data_send)
            except Exception as e:
                print(f"❌ Lỗi emit_chat_message_sync: {e}")

    except KeyboardInterrupt:
        print("🔝 Logger process interrupted with Ctrl+C. Exiting gracefully.")
    finally:
        session.close()
        mt5.shutdown()

def update_statistics(session, login: int, total_pnl: float):
    today = datetime.now().date()
    week_str = datetime.now().strftime("%Y-%W")
    month_str = datetime.now().strftime("%Y-%m")

    stat = session.query(StatisticalPNL).filter_by(login=login).first()
    if not stat:
        stat = StatisticalPNL(login=login)
        session.add(stat)

    # --- Ngày ---
    day_high = session.query(func.max(MultiAccountPnL_D.high)).filter_by(login=login).scalar() or total_pnl
    day_low = session.query(func.min(MultiAccountPnL_D.low)).filter_by(login=login).scalar() or total_pnl

    if total_pnl > day_high:
        day_change = total_pnl - day_low
    elif total_pnl < day_low:
        day_change = day_high - total_pnl
    else:
        day_change = day_high - day_low

    if not stat.best_day_change or day_change > stat.best_day_change:
        stat.best_day_change = day_change
        stat.best_day = today
    if not stat.worst_day_change or day_change < stat.worst_day_change:
        stat.worst_day_change = day_change
        stat.worst_day = today

    stat.day_max = max(day_high, total_pnl)
    stat.day_min = min(day_low, total_pnl)

    # --- Tuần ---
    week_high = session.query(func.max(MultiAccountPnL_W.high)).filter_by(login=login).scalar() or total_pnl
    week_low = session.query(func.min(MultiAccountPnL_W.low)).filter_by(login=login).scalar() or total_pnl

    if total_pnl > week_high:
        week_change = total_pnl - week_low
    elif total_pnl < week_low:
        week_change = week_high - total_pnl
    else:
        week_change = week_high - week_low

    if not stat.best_week_change or week_change > stat.best_week_change:
        stat.best_week_change = week_change
        stat.best_week = week_str
    if not stat.worst_week_change or week_change < stat.worst_week_change:
        stat.worst_week_change = week_change
        stat.worst_week = week_str

    stat.week_max = max(week_high, total_pnl)
    stat.week_min = min(week_low, total_pnl)

    # --- Tháng ---
    month_high = session.query(func.max(MultiAccountPnL_MN.high)).filter_by(login=login).scalar() or total_pnl
    month_low = session.query(func.min(MultiAccountPnL_MN.low)).filter_by(login=login).scalar() or total_pnl

    if total_pnl > month_high:
        month_change = total_pnl - month_low
    elif total_pnl < month_low:
        month_change = month_high - total_pnl
    else:
        month_change = month_high - month_low

    if not stat.best_month_change or month_change > stat.best_month_change:
        stat.best_month_change = month_change
        stat.best_month = month_str
    if not stat.worst_month_change or month_change < stat.worst_month_change:
        stat.worst_month_change = month_change
        stat.worst_month = month_str

    stat.month_max = max(month_high, total_pnl)
    stat.month_min = min(month_low, total_pnl)

    stat.time = datetime.now()
    session.merge(stat)