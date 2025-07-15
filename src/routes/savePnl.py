import MetaTrader5 as mt5
import os
import time
from datetime import datetime
import multiprocessing
import pandas as pd
import json
from src.models.modelMultiAccountPnL import MultiAccountPnL
from src.models.model import SessionLocal
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from src.models.modelAccMt5 import AccountMt5
import asyncio

terminals = {
    "Acc1": "C:/Program Files/MetaTrader 5 - acc 1/terminal64.exe",
    "Acc2": "C:/Program Files/MetaTrader 5 - acc 2/terminal64.exe",
}

def monitor_account(mt5_path, account_name, interval, queue):
    db = SessionLocal()
    while True:
        if not mt5.initialize(path=mt5_path):
            print(f"[{account_name}] ❌ Cannot initialize MT5 at {mt5_path}")
            time.sleep(interval)
            continue

        account_info = mt5.account_info()
        positions = mt5.positions_get()

        existing = db.query(AccountMt5).filter(AccountMt5.username == account_info.login).all()
        if (len(existing) == 0):
            new_data = AccountMt5(username=account_info.login, password='', loginId=1, server=account_info.server)
            db.add(new_data)
            db.commit()

        symbol_pnls = {}
        for pos in positions:
            symbol = pos.symbol
            symbol_pnls[symbol] = symbol_pnls.get(symbol, 0.0) + pos.profit

        if account_info:
            num_positions = len(positions) if positions else 0
            data = {
                "login": account_info.login,
                "time": datetime.now().isoformat(),
                "total_pnl": account_info.profit,
                "by_symbol": json.dumps({k: round(v, 2) for k, v in symbol_pnls.items()}),
                "num_positions": num_positions
            }
            log = MultiAccountPnL(
                login=account_info.login,
                total_pnl=account_info.profit,
                num_positions=num_positions,
                time=datetime.now(),
                by_symbol=json.dumps({k: round(v, 2) for k, v in symbol_pnls.items()})
            )

            db.add(log)
            db.commit()
            print(f"✅ Đã ghi PnL {account_info.login}: {account_info.profit} với {num_positions} lệnh")
            queue.put(data)  # 👉 gửi về process ghi log

        mt5.shutdown()
        time.sleep(interval)

def logger_process(queue: multiprocessing.Queue, csv_path="src/pnl_cache/pnl_log.csv", excel_path="src/pnl_cache/pnl_log.xlsx"):
    os.makedirs("src/pnl_cache", exist_ok=True)

    while True:
        data = queue.get()  # chặn đến khi có dữ liệu
        df = pd.DataFrame([data])

        if not os.path.exists(csv_path):
            df.to_csv(csv_path, index=False)
        else:
            df.to_csv(csv_path, mode="a", header=False, index=False)

        try:
            if not os.path.exists(excel_path):
                # 👉 Tạo file mới nếu chưa có
                wb = Workbook()
                ws = wb.active
                ws.append(list(data.keys()))  # Ghi header
            else:
                # 👉 Mở file có sẵn
                wb = load_workbook(excel_path)
                ws = wb.active

            # 👉 Ghi dữ liệu mới vào dòng tiếp theo
            ws.append(list(data.values()))

            # 👉 Tự động điều chỉnh độ rộng cột (tuỳ chọn)
            for i, column in enumerate(data.keys(), 1):
                col_letter = get_column_letter(i)
                max_length = max(
                    [len(str(cell.value)) for cell in ws[col_letter]] + [len(column)]
                )
                ws.column_dimensions[col_letter].width = max_length + 2

            wb.save(excel_path)
        except Exception as e:
            print(f"⚠️ Error writing Excel: {e}")

def run_save_pnl_blocking():
    multiprocessing.freeze_support()
    queue = multiprocessing.Queue()

    log_proc = multiprocessing.Process(target=logger_process, args=(queue,))
    log_proc.start()

    processes = []
    for name, path in terminals.items():
        p = multiprocessing.Process(target=monitor_account, args=(path, name, 10, queue))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()
    log_proc.join()

async def run_save_pnl():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_save_pnl_blocking)