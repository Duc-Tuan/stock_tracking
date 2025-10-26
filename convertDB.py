from sqlalchemy.orm import sessionmaker
from collections import defaultdict
from sqlalchemy import create_engine
from datetime import datetime, timedelta, timezone
from src.models.modelPNL import (
    MultiAccountPnL_M1, MultiAccountPnL_H1, MultiAccountPnL_H2, MultiAccountPnL_H4,
    MultiAccountPnL_H6, MultiAccountPnL_H8, MultiAccountPnL_H12,
    MultiAccountPnL_D, MultiAccountPnL_W, MultiAccountPnL_MN,
)

# --- Connect database ---
DATABASE_URL = "sqlite:///./pnl.db"  # Thay bằng URL DB của bạn
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

# --- Load dữ liệu M1 ---
m1_data = session.query(MultiAccountPnL_M1).all()

# --- Gom theo login và 5 phút ---
# --- Gom theo VN timezone +7 ---
VN_TZ = timezone(timedelta(hours=7))

grouped = defaultdict(list)
for row in m1_data:
    # time chỉ lưu HH:MM:00
    # hour = row.time.hour
    # minute = (row.time.minute // 30) * 30  # tròn xuống 10 phút
    # time_key = row.time.replace(hour=hour, minute=minute, second=0, microsecond=0)
    # grouped[(row.login, time_key)].append(row)

    # hour = row.time.hour  # giờ hiện tại
    # hour = (row.time.hour // 12) * 12  # giờ tròn 2 tiếng
    # time_key = row.time.replace(hour=hour, minute=0, second=0, microsecond=0)
    # grouped[(row.login, time_key)].append(row)

    # Chuẩn hóa thời gian sang VN timezone
    # if row.time.tzinfo is None:
    #     dt_vn = row.time.replace(tzinfo=VN_TZ)
    # else:
    #     dt_vn = row.time.astimezone(VN_TZ)
    
    # weekday = dt_vn.weekday()  # Thứ 2 = 0, Thứ 7 = 5
    # hour = dt_vn.hour

    # Thứ 2 đặc biệt
    # if weekday == 0:
    #     if 4 <= hour < 7:
    #         # Phiên sáng sớm 4h-7h, gán cùng ngày
    #         date_key = row.time.replace(hour=4, minute=0, second=0, microsecond=0)
    #     else:
    #         # Phiên chính: 7h → 7h hôm sau
    #         if hour >= 7:
    #             date_key = row.time.replace(hour=7, minute=0, second=0, microsecond=0)
    #         else:
    #             # 0h-4h: thuộc ngày hôm trước (phiên chính)
    #             date_key = (row.time - timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0)
    # else:
    #     # Ngày bình thường: 7h → 7h hôm sau
    #     if hour >= 7:
    #         date_key = row.time.replace(hour=7, minute=0, second=0, microsecond=0)
    #     else:
    #         date_key = (row.time - timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0)
    
    # grouped[(row.login, date_key)].append(row)

    # Xác định thứ 2 của tuần hiện tại
    # weekday = dt_vn.weekday()  # Thứ 2 = 0
    # # Nếu ngày trước thứ 2 7h thì sẽ thuộc tuần trước
    # if weekday < 0 or (weekday == 0 and dt_vn.hour < 7):
    #     monday_dt = dt_vn - timedelta(days=weekday + 7)
    # else:
    #     monday_dt = dt_vn - timedelta(days=weekday)
    
    # # Time key = 07:00 thứ 2
    # week_key = monday_dt.replace(hour=7, minute=0, second=0, microsecond=0)
    # grouped[(row.login, week_key)].append(row)

    month = row.time.month + 1
    month_key = row.time.replace(month=month,day=1, hour=0, minute=0, second=0, microsecond=0)
    grouped[(row.login, month_key)].append(row)

# --- Tạo record M5 ---
m5_records = []
for (login, time_key), rows in grouped.items():
    rows = sorted(rows, key=lambda x: x.time)
    open_ = rows[0].open
    close_ = rows[-1].close
    high_ = max(r.high for r in rows)
    low_ = min(r.low for r in rows)
    # P = (low + high + close)/3
    P_ = (low_ + high_ + close_) / 3

    m5 = MultiAccountPnL_MN(
        login=login,
        time=time_key,
        open=open_,
        high=high_,
        low=low_,
        close=close_,
        P=P_
    )
    m5_records.append(m5)

# --- Ghi vào database ---
if m5_records:
    session.bulk_save_objects(m5_records)
    session.commit()
    print(f"Đã gom {len(m5_records)} nến H1 từ M1.")
else:
    print("Không có dữ liệu để gom.")

session.close()