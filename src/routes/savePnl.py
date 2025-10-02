import time
import json
import traceback
import MetaTrader5 as mt5
from datetime import datetime
import queue as pyqueue
from sqlalchemy.orm import Session

from src.models.modelMultiAccountPnL import MultiAccountPnL
from src.models.model import SessionLocal
from src.models.modelAccMt5 import AccountMt5
from src.utils.stop import swap_difference
from src.services.socket_manager import emit_chat_message_sync

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

                    # === Lưu vào DB ===
                    record = MultiAccountPnL(
                        login=account_info.login,
                        time=datetime.now(),
                        total_pnl=total_pnl,
                        num_positions=num_positions,
                        by_symbol=by_symbol_json,
                    )
                    session.add(record)
                    session.commit()

                    data_send = {
                        "login": account_info.login,
                        "total_pnl": total_pnl,
                        "by_symbol": by_symbol_json,
                        "time": datetime.now().isoformat(),
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