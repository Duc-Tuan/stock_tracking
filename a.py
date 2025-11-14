# save as fx_stats_10y.py
# pip install pandas requests python-dateutil
import requests
import io
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser

# cấu hình
symbols = {
    "AUDCAD":"audcad",
    "NZDCAD":"nzdcad",
    "AUDNZD":"audnzd",
    "CADCHF":"cadchf",
    "EURCHF":"eurchf",
    "EURGBP":"eurgbp",

    "EURJPY":"eurjpy",
    "CADJPY":"cadjpy",
    "AUDJPY":"audjpy",
    "CHFJPY":"chfjpy",
    "GBPJPY":"gbpjpy",
    "NZDJPY":"nzdjpy",
}
# Ổn định: ngày cuối cùng là 2025-11-12 theo yêu cầu
END_DATE = datetime(2025,11,12).date()
START_DATE = END_DATE - timedelta(days=365*10 + 30)  # thêm 30 ngày đệm cho an toàn

def download_stooq_csv(sym):
    """Download CSV from Stooq. URL: https://stooq.com/q/d/l/?s=<sym>&i=d"""
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text

def parse_csv_to_df(csv_text):
    df = pd.read_csv(io.StringIO(csv_text), parse_dates=['Date'])
    # Stooq CSV format: Date,Open,High,Low,Close,Volume
    df = df.rename(columns={c:c.strip() for c in df.columns})
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    return df

def compute_stats_for_df(df):
    # filter 10y range
    mask = (df['Date'] >= START_DATE) & (df['Date'] <= END_DATE)
    df10 = df.loc[mask].copy()
    if df10.empty:
        return None
    # Highest price (high) and its date(s) — user asked "giá cao nhất trên khung D"
    idx_high = df10['High'].idxmax()
    highest = df10.loc[idx_high, 'High']
    highest_date = df10.loc[idx_high, 'Date']
    # Lowest price (low) and date
    idx_low = df10['Low'].idxmin()
    lowest = df10.loc[idx_low, 'Low']
    lowest_date = df10.loc[idx_low, 'Date']
    # Candle with highest high: range = high - low on that same row
    idx_candle_high = idx_high
    range_candle_high = df10.loc[idx_candle_high, 'High'] - df10.loc[idx_candle_high, 'Low']
    # Candle with lowest low: range = high - low on that same row
    idx_candle_low = idx_low
    range_candle_low = df10.loc[idx_candle_low, 'High'] - df10.loc[idx_candle_low, 'Low']
    return {
        "highest": (float(highest), highest_date.isoformat()),
        "lowest": (float(lowest), lowest_date.isoformat()),
        "range_on_highest_high_candle": float(range_candle_high),
        "range_on_lowest_low_candle": float(range_candle_low),
        "rows_checked": len(df10)
    }

def main():
    results = {}
    for name, sym in symbols.items():
        try:
            print(f"Downloading {name} from Stooq...")
            csv_text = download_stooq_csv(sym)
            df = parse_csv_to_df(csv_text)
            stats = compute_stats_for_df(df)
            if stats is None:
                print(f"  Không có dữ liệu 10 năm cho {name}")
                results[name] = None
            else:
                results[name] = stats
                print(f"  Done: checked {stats['rows_checked']} rows")
        except Exception as e:
            print(f"  Lỗi khi xử lý {name}: {e}")
            results[name] = {"error": str(e)}
    # In đẹp
    print("\nKẾT QUẢ (10 năm tới {:%Y-%m-%d}):".format(END_DATE))
    for name, v in results.items():
        print("\n=== ", name)
        if v is None:
            print("  No data")
            continue
        if 'error' in v:
            print("  Error:", v['error'])
            continue
        print(f"  1) Giá cao nhất (High): {v['highest'][0]:.6f}  — ngày {v['highest'][1]}")
        print(f"  2) Giá thấp nhất (Low) : {v['lowest'][0]:.6f}  — ngày {v['lowest'][1]}")
        print(f"  3) Lần tăng mạnh nhất (range của cây có HIGH lớn nhất): {v['range_on_highest_high_candle']:.6f}")
        print(f"  4) Lần giảm mạnh nhất (range của cây có LOW thấp nhất):  {v['range_on_lowest_low_candle']:.6f}")
    # bạn có thể lưu results ra JSON/CSV nếu muốn
    return results

if __name__ == '__main__':
    main()
