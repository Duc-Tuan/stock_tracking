import time
import json
import traceback
import MetaTrader5 as mt5
from datetime import datetime, date
import queue as pyqueue
from sqlalchemy.orm import Session

from src.models.modelstatisticalPnl import StatisticalPNL
from src.models.model import SessionLocal
from src.models.modelAccMt5 import AccountMt5
from src.utils.stop import swap_difference
from src.services.socket_manager import emit_chat_message_sync
from src.services.save_pnl_aggregator import save_pnl_to_timeframes

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

                if account_info:
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
            except Exception as e:
                session.rollback()
                print(f"❌ Lỗi trong monitor_account: {e}")
                traceback.print_exc()
                continue
            
            # ✅ luôn gửi socket, kể cả khi auto_send_order_acc_transaction bị lỗi
            try:
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
    if stat.best_day != today:
        stat.day_min = total_pnl
        stat.day_max = total_pnl
        stat.best_day = today
        stat.best_day_change = 0
        stat.worst_day = today
        stat.worst_day_change = 0
    else:
        stat.day_min = min(stat.day_min, total_pnl)
        stat.day_max = max(stat.day_max, total_pnl)
        change = stat.day_max - stat.day_min
        if change > (stat.best_day_change or 0):
            stat.best_day_change = change
            stat.best_day = today
        if change < (stat.worst_day_change or 0):
            stat.worst_day_change = change
            stat.worst_day = today

    # --- Tuần ---
    if stat.best_week != week_str:
        stat.week_min = total_pnl
        stat.week_max = total_pnl
        stat.best_week = week_str
        stat.best_week_change = 0
        stat.worst_week = week_str
        stat.worst_week_change = 0
    else:
        stat.week_min = min(stat.week_min, total_pnl)
        stat.week_max = max(stat.week_max, total_pnl)
        change = stat.week_max - stat.week_min
        if change > (stat.best_week_change or 0):
            stat.best_week_change = change
            stat.best_week = week_str
        if change < (stat.worst_week_change or 0):
            stat.worst_week_change = change
            stat.worst_week = week_str

    # --- Tháng ---
    if stat.best_month != month_str:
        stat.month_min = total_pnl
        stat.month_max = total_pnl
        stat.best_month = month_str
        stat.best_month_change = 0
        stat.worst_month = month_str
        stat.worst_month_change = 0
    else:
        stat.month_min = min(stat.month_min, total_pnl)
        stat.month_max = max(stat.month_max, total_pnl)
        change = stat.month_max - stat.month_min
        if change > (stat.best_month_change or 0):
            stat.best_month_change = change
            stat.best_month = month_str
        if change < (stat.worst_month_change or 0):
            stat.worst_month_change = change
            stat.worst_month = month_str

    stat.time = datetime.now()
    session.merge(stat)
    # session.commit()
