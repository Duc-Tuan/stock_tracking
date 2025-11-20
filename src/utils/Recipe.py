from typing import List, Dict
import math

def calculate_bollinger_bands(data, period=20, k=2):
    period = int(period)   # Ép về integer để tránh lỗi
    k = float(k)

    if len(data) < period:
        return []

    bands = []

    for i in range(period - 1, len(data)):
        slice_data = [d["close"] for d in data[i - period + 1 : i + 1]]

        mean = sum(slice_data) / period
        variance = sum((x - mean) ** 2 for x in slice_data) / period
        std_dev = variance ** 0.5

        bands.append({
            "time": data[i]["time"],
            "ma": mean,
            "upper": mean + k * std_dev,
            "lower": mean - k * std_dev,
        })

    return bands


def calculate_rsi(data: List[Dict], period=14):
    if not data or len(data) <= period:
        return []

    # ----- CHECK xem dữ liệu có đang newest → oldest không -----
    # Nếu time[0] > time[-1] nghĩa là đang newest-first → đảo lại
    if data[0]["time"] > data[-1]["time"]:
        data = list(reversed(data))

    rsi = []
    gains = []
    losses = []

    # ----- Tính gain/loss -----
    for i in range(1, len(data)):
        change = data[i]["close"] - data[i - 1]["close"]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    # ----- SMA đầu -----
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    def calc_rsi(avg_g, avg_l):
        if avg_g == 0 and avg_l == 0:
            return 50
        if avg_l == 0:
            return 100
        rs = avg_g / avg_l
        return 100 - (100 / (1 + rs))

    # RSI đầu tiên
    rsi.append({
        "time": data[period]["time"],
        "value": calc_rsi(avg_gain, avg_loss)
    })

    # ----- Wilder smoothing -----
    for i in range(period + 1, len(data)):
        change = data[i]["close"] - data[i - 1]["close"]
        gain = max(change, 0)
        loss = max(-change, 0)

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        rsi.append({
            "time": data[i]["time"],
            "value": calc_rsi(avg_gain, avg_loss)
        })

    return rsi
