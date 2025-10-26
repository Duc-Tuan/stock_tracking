from datetime import datetime, timedelta, timezone
import math
from src.models.modelPNL import (
    MultiAccountPnL_M1, MultiAccountPnL_M5, MultiAccountPnL_M10,
    MultiAccountPnL_M15, MultiAccountPnL_M30,
    MultiAccountPnL_H1, MultiAccountPnL_H2, MultiAccountPnL_H4,
    MultiAccountPnL_H6, MultiAccountPnL_H8, MultiAccountPnL_H12,
    MultiAccountPnL_D, MultiAccountPnL_W, MultiAccountPnL_MN,
)

TIMEFRAME_MODELS = {
    "M1": MultiAccountPnL_M1,
    "M5": MultiAccountPnL_M5,
    "M10": MultiAccountPnL_M10,
    "M15": MultiAccountPnL_M15,
    "M30": MultiAccountPnL_M30,
    "H1": MultiAccountPnL_H1,
    "H2": MultiAccountPnL_H2,
    "H4": MultiAccountPnL_H4,
    "H6": MultiAccountPnL_H6,
    "H8": MultiAccountPnL_H8,
    "H12": MultiAccountPnL_H12,
    "D": MultiAccountPnL_D,
    "W": MultiAccountPnL_W,
    "MN": MultiAccountPnL_MN,
}

TIMEFRAMES = {
    "M1": timedelta(minutes=1),
    "M5": timedelta(minutes=5),
    "M10": timedelta(minutes=10),
    "M15": timedelta(minutes=15),
    "M30": timedelta(minutes=30),
    "H1": timedelta(hours=1),
    "H2": timedelta(hours=2),
    "H4": timedelta(hours=4),
    "H6": timedelta(hours=6),
    "H8": timedelta(hours=8),
    "H12": timedelta(hours=12),
    "D": timedelta(days=1),
    "W": timedelta(weeks=1),
    "MN": "month",
}

def localize_to_vn(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=7)))
    else:
        dt = dt.astimezone(timezone(timedelta(hours=7)))
    return dt

def get_daily_candle_start(now: datetime) -> datetime:
    now = localize_to_vn(now)
    weekday = now.weekday()  # 0 = thứ 2
    hour = now.hour

    if weekday == 0:  # Thứ 2
        if hour < 7:
            # Phiên 1 (4h - 7h)
            return datetime(now.year, now.month, now.day, 4)
        else:
            # Phiên 2 (7h - 7h hôm sau)
            return datetime(now.year, now.month, now.day, 7)
    else:
        # Các ngày khác: 7h - 7h hôm sau
        if hour < 7:
            # vẫn thuộc nến hôm trước
            prev_day = now - timedelta(days=1)
            return datetime(prev_day.year, prev_day.month, prev_day.day, 7)
        else:
            return datetime(now.year, now.month, now.day, 7)
        
def save_pnl_to_timeframes(session, login: int, total_pnl: float):
    now = datetime.now()
    for tf, Model in TIMEFRAME_MODELS.items():
        if tf == "D":
            start_time = get_daily_candle_start(now)
        elif tf == "W":
            start_of_week = now - timedelta(days=now.weekday())
            start_time = datetime(start_of_week.year, start_of_week.month, start_of_week.day, 7)
        elif tf == "MN":
            start_time = datetime(now.year, now.month, 1, 7)
        else:
            delta = TIMEFRAMES[tf]
            total_seconds = int(now.timestamp())
            tf_seconds = int(delta.total_seconds())
            start_timestamp = (total_seconds // tf_seconds) * tf_seconds
            start_time = datetime.fromtimestamp(start_timestamp)

        existing = session.query(Model).filter(
            Model.login == login,
            Model.time == start_time
        ).first()
        if existing:
            existing.high = max(existing.high, total_pnl)
            existing.low = min(existing.low, total_pnl)
            existing.close = total_pnl
            existing.P = math.ceil((existing.close + existing.high + existing.low) / 3 * 100) / 100
            session.merge(existing)
        else:
            record = Model(
                login=login,
                time=start_time,
                open=total_pnl,
                high=total_pnl,
                low=total_pnl,
                close=total_pnl,
                P=math.ceil((total_pnl + total_pnl + total_pnl) / 3 * 100) / 100
            )
            session.add(record)
