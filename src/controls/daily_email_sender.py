import smtplib
import schedule
import os
import json
import asyncio

import pandas as pd
from datetime import datetime
from openpyxl.utils import get_column_letter

from fastapi import HTTPException
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from src.utils.options import SENDER_PASSWORD, SENDER_EMAIL, SEND_TIME

# ======== CẤU HÌNH NGƯỜI GỬI & NGƯỜI NHẬN =========
RECEIVER_EMAIL = "testsendpymt5@gmail.com"  # Hoặc danh sách: ["a@a.com", "b@b.com"]
ATTACHMENT_PATH = "src/pnl_cache/pnl_log.xlsx"  # Đường dẫn file đính kèm

rename_map = {
    "login": "Tài khoản",
    "time": "Thời gian",
    "total_pnl": "Lợi nhuận tổng",
    "num_positions": "Số lệnh",
    "by_symbol": "Chi tiết theo cặp"
}

# ✅ Xử lý cột by_symbol an toàn
def parse_symbol(s):
    try:
        if s is None or s != s:
            return {}
        if isinstance(s, dict):
            return s
        if isinstance(s, str):
            s = s.strip()
            if s.lower() in ["", "null", "none"]:
                return {}
            return json.loads(s.replace("'", '"'))
        return {}
    except:
        return {}

def send_email_with_attachment():
    print("📤 Đang gửi email...")

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL if isinstance(RECEIVER_EMAIL, str) else ", ".join(RECEIVER_EMAIL)
    msg['Subject'] = "📊 Báo cáo định kỳ theo ngày kèm file"

    SEND_TIME_NOW = datetime.now().strftime("%d/%m/%Y")
    body = f"Chào sếp,\n\nĐây là báo cáo định kỳ vào lúc {SEND_TIME} ngày {SEND_TIME_NOW} có kèm file đính kèm ở bên dưới.\n\nTrân trọng."
    msg.attach(MIMEText(body, 'plain'))


    # gửi file .excel
    try:
        df = pd.read_excel(ATTACHMENT_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đọc file Excel gốc: {e}")

    df["by_symbol"] = df["by_symbol"].apply(parse_symbol)

    file_name = f"pnl_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
        for login_id, group in df.groupby("login"):
            group = group.reset_index(drop=True)

            # 👉 Chuyển mỗi dict trong 'by_symbol' thành cột mới cùng hàng
            expanded = group["by_symbol"].apply(pd.Series)
            merged_df = pd.concat([group.drop(columns=["by_symbol"]), expanded], axis=1)

            # 👉 Đổi tên cột nếu khớp với rename_map
            renamed_df = merged_df.rename(columns=rename_map)

            sheet_name = str(login_id)
            renamed_df.to_excel(writer, sheet_name=sheet_name, index=False)

            # 📏 Tự động điều chỉnh độ rộng cột
            worksheet = writer.sheets[sheet_name]
            for idx, col in enumerate(renamed_df.columns, 1):
                try:
                    max_len = renamed_df[col].apply(lambda x: len(str(x)) if pd.notna(x) else 0).max()
                    adjusted_width = min(max(max_len, len(str(col))) + 2, 50)
                    worksheet.column_dimensions[get_column_letter(idx)].width = adjusted_width
                except Exception as e:
                    print(f"⚠️ Lỗi khi xử lý cột {col}: {e}")
                    worksheet.column_dimensions[get_column_letter(idx)].width = 20

    # ======= TẠO FILE CSV =========
    csv_file = "src/pnl_cache/pnl_log.csv"
    df.to_csv(csv_file, index=False)
    
     # ======= ĐÍNH KÈM CẢ 2 FILE =========
    file_list = [file_name, csv_file]
    for file_path in file_list:
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={os.path.basename(file_path)}'
                )
                msg.attach(part)
        else:
            print(f"⚠️ File không tồn tại: {file_path}")

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("✅ Email đã được gửi thành công.")
    except Exception as e:
        print("❌ Lỗi khi gửi email:", e)

    # (Tùy chọn) Xoá file tạm
    if os.path.exists(file_name):
        os.remove(file_name)

# ========= LỊCH GỬI =========
schedule.every().day.at(SEND_TIME).do(send_email_with_attachment)

async def run_schedule_email():
    print(f"🕒 Script chạy, chờ gửi email mỗi ngày lúc {SEND_TIME}...")
    while True:
        schedule.run_pending()
        await asyncio.sleep(60)
