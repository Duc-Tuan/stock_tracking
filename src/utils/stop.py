import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from datetime import datetime, time
from datetime import datetime, time as dtime, timedelta
from src.models.modelSwapMt5 import SwapMt5

def swap_difference(db, account_info):
    def get_log_for_day(day_date):
        start = datetime.combine(day_date, dtime(0, 0))              # 00:00:00
        end = datetime.combine(day_date, dtime(23, 59, 59, 999999))  # 23:59:59.999999
        return db.query(SwapMt5).filter(
            SwapMt5.username == account_info.login,
            SwapMt5.created_at.between(start, end)
        ).order_by(SwapMt5.created_at.desc()).first()

    now = datetime.now()
    today_date = now.date()
    yesterday_date = today_date - timedelta(days=1)

    # ✅ Tính mốc thời gian cắt ngày theo mùa
    if 4 <= now.month <= 9:
        cut_off = dtime(4, 3)  # mùa hè: 04:03
    else:
        cut_off = dtime(5, 3)  # mùa đông: 05:03

    if now.time() < cut_off:
        today_date = yesterday_date
        yesterday_date = today_date - timedelta(days=1)

    today_log = get_log_for_day(today_date)
    yesterday_log = get_log_for_day(yesterday_date)

    if yesterday_log and today_log:
        print(f"Tài khoản {account_info.login} swap hôm qua: {yesterday_log.swap}, hôm nay: {today_log.swap}")
        return today_log.swap - yesterday_log.swap

    return 0