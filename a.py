from datetime import timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.modelMultiAccountPnL import MultiAccountPnL
from src.models.modelPNL import (
    MultiAccountPnL_M1, MultiAccountPnL_M5, MultiAccountPnL_M10,
    MultiAccountPnL_M15, MultiAccountPnL_M30,
    MultiAccountPnL_H1, MultiAccountPnL_H2, MultiAccountPnL_H4,
    MultiAccountPnL_H6, MultiAccountPnL_H8, MultiAccountPnL_H12,
    MultiAccountPnL_D, MultiAccountPnL_W, MultiAccountPnL_MN,
)
import pandas as pd
import gc
from src.models.model import Base as Base2

# ------------------- Config -------------------
DB_PATH = "sqlite:///./pnl.db"
engine = create_engine(DB_PATH)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

Base2.metadata.create_all(engine)

# ------------------- Hàm tính aggregate -------------------
def aggregate(df_group):
    open_ = df_group.iloc[0]["total_pnl"]
    close = df_group.iloc[-1]["total_pnl"]
    high = df_group["total_pnl"].max()
    low = df_group["total_pnl"].min()
    P = (close + high + low) / 3
    time = df_group.iloc[-1]["time"]
    login = df_group.iloc[-1]["login"]
    return {
        "login": login,
        "time": time,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "P": P,
    }

# ------------------- Các khung thời gian -------------------
def round_time(df, freq):
    return df.groupby(["login", pd.Grouper(key="time", freq=freq)])

timeframes = {
    "M1": (MultiAccountPnL_M1, "1min"),
    "M5": (MultiAccountPnL_M5, "5min"),
    "M10": (MultiAccountPnL_M10, "10min"),
    "M15": (MultiAccountPnL_M15, "15min"),
    "M30": (MultiAccountPnL_M30, "30min"),

    "H1": (MultiAccountPnL_H1, "1h"),
    "H2": (MultiAccountPnL_H2, "2h"),
    "H4": (MultiAccountPnL_H4, "4h"),
    "H6": (MultiAccountPnL_H6, "6h"),
    "H8": (MultiAccountPnL_H8, "8h"),
    "H12": (MultiAccountPnL_H12, "12h"),

    "W": (MultiAccountPnL_W, "1W"),
    "MN": (MultiAccountPnL_MN, "1ME"),
}

# ------------------- Gom theo "ngày trade" (07h–07h) -------------------
def group_custom_day(df):
    df = df.copy()

    # Chuẩn hóa timezone VN
    if df["time"].dt.tz is None:
        df["time"] = df["time"].dt.tz_localize("Asia/Bangkok")
    else:
        df["time"] = df["time"].dt.tz_convert("Asia/Bangkok")

    df["shifted_time"] = df["time"] - pd.Timedelta(hours=7)
    df["trade_day"] = df["shifted_time"].dt.date

    def adjust_for_monday(row):
        weekday = row["time"].weekday()
        hour = row["time"].hour
        if weekday == 0 and 4 <= hour < 7:
            return f"{row['time'].date()}_mon_early"
        return str(row["trade_day"])

    df["trade_day"] = df.apply(adjust_for_monday, axis=1)
    return df.groupby(["login", "trade_day"])

# ------------------- Hàm sửa lỗi encoding -------------------
def fix_encoding(s):
    if not isinstance(s, str):
        return s
    try:
        # Thử decode nếu bị lỗi cp1252 → utf-8
        return s.encode("latin1").decode("utf-8")
    except Exception:
        try:
            # Nếu vẫn lỗi thì bỏ ký tự không hợp lệ
            return s.encode("utf-8", "ignore").decode("utf-8")
        except Exception:
            return s

# ------------------- Bắt đầu xử lý theo batch -------------------
print("Đang đọc dữ liệu gốc (chia batch 1_000_000 dòng)...")

BATCH_SIZE = 1_000_000
offset = 0
total_processed = 0

while True:
    batch = (
        session.query(MultiAccountPnL)
        .order_by(MultiAccountPnL.id)
        .offset(offset)
        .limit(BATCH_SIZE)
        .all()
    )

    if not batch:
        break

    print(f"\n🟩 Đang xử lý batch {offset} → {offset + len(batch)} ({len(batch)} dòng)")

    # Convert batch sang DataFrame
    rows = [{
        "id": d.id,
        "login": d.login,
        "time": d.time,
        "total_pnl": d.total_pnl,
        "num_positions": d.num_positions,
        "by_symbol": d.by_symbol,
    } for d in batch]

    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"])

    # 🔧 Fix lỗi encoding cột login
    df["login"] = df["login"].astype(str).apply(fix_encoding)
    if any("�" in s for s in df["login"]):
        print("⚠️  Cảnh báo: Có ký tự lỗi trong login, đã cố gắng khôi phục encoding.")

    # ---- Xử lý từng timeframe (M1–MN trừ D) ----
    for tf_name, (Model, freq) in timeframes.items():
        print(f"  ➜ Timeframe: {tf_name} ({freq})...")
        grouped = round_time(df, freq)
        result_rows = [aggregate(g) for _, g in grouped]
        objs = [Model(**r) for r in result_rows]
        session.bulk_save_objects(objs)
        session.commit()
        print(f"     ✅ Đã ghi {len(objs)} dòng vào {Model.__tablename__}")

    # ---- Xử lý timeframe D ----
    print("  ➜ Timeframe D (07h–07h, tách thứ 2)...")
    grouped_d = group_custom_day(df)
    result_rows_d = [aggregate(g) for _, g in grouped_d]
    objs_d = [MultiAccountPnL_D(**r) for r in result_rows_d]
    session.bulk_save_objects(objs_d)
    session.commit()
    print(f"     ✅ Đã ghi {len(objs_d)} dòng vào {MultiAccountPnL_D.__tablename__}")

    # ---- Dọn RAM ----
    total_processed += len(batch)
    del df, rows, batch, result_rows, result_rows_d, objs, objs_d
    gc.collect()

    offset += BATCH_SIZE

print(f"\n🎯 Hoàn tất xử lý toàn bộ dữ liệu ({total_processed:,} dòng)!")
