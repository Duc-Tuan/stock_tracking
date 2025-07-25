import MetaTrader5 as mt5
from src.models.model import SessionLocal
from src.models.modelAccMt5 import AccountMt5
from src.models.modelSwapMt5 import SwapMt5
from datetime import datetime, timedelta
import schedule
import asyncio
import MetaTrader5 as mt5
import time
from src.utils.options import SEND_TIME_UPDATE_SWAP_SUMMER, SEND_TIME_UPDATE_SWAP_WINTER

def log_daily_swap(db, account_info, total_swap):
    new_entry = SwapMt5(
        username=str(account_info.login),
        server=account_info.server,
        swap=total_swap,
        created_at=datetime.utcnow() + timedelta(hours=7)  # VN time
    )
    db.add(new_entry)
    db.commit()
    print(f"✅ Đã lưu swap lúc {new_entry.created_at}, giá trị: {total_swap}", 'info')

def update_swap_mt5(positions, account_info):
    db = SessionLocal()
    try:
        total_swap = 0

        for pos in positions:
            total_swap += pos.swap

        return log_daily_swap(db, account_info, total_swap)
    except Exception as e:
        print(f"❌ Lỗi khi lưu phí qua đêm: {e}")

def get_swap_time_str_vietnam():
    """Trả về giờ chạy swap theo mùa (mùa hè: 4h, mùa đông: 5h) - tính theo giờ Việt Nam"""
    now = datetime.now()
    month = now.month
    # Mùa hè: từ tháng 4 đến hết tháng 10
    if 4 <= month <= 10:
        return SEND_TIME_UPDATE_SWAP_SUMMER
    else:
        return SEND_TIME_UPDATE_SWAP_WINTER

def daily_swap_process(terminals):

    def job():
        for name, path in terminals.items():
            if not mt5.initialize(path):
                print(f"⚠️ Không khởi tạo được MT5: {path}")
                continue
            account_info = mt5.account_info()
            positions = mt5.positions_get()
            if account_info and positions:
                update_swap_mt5(positions, account_info)
            mt5.shutdown()

    SEND_TIME_UPDATE_SWAP = get_swap_time_str_vietnam()
    schedule.every().day.at(SEND_TIME_UPDATE_SWAP).do(job)

    print(f"🕒 daily_swap_process: Sẽ chạy lúc {SEND_TIME_UPDATE_SWAP} sáng mỗi ngày...")

    while True:
        schedule.run_pending()
        time.sleep(60)