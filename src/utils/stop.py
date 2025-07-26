from datetime import datetime, time

def stopDef(now: datetime) -> bool:
    # Trả về True nếu:
    # - Chủ nhật (nguyên ngày)
    # - Thứ bảy trước 07:00
    # - Thứ hai trước 03:59
    weekday = now.weekday()
    current_time = now.time()

    if weekday == 6:  # Chủ nhật
        return True
    elif weekday == 5 and current_time >= time(7, 00):  # Thứ bảy trước 07:00
        return True
    elif weekday == 0 and current_time < time(3, 59):  # Thứ hai trước 03:59
        return True
    return False
    