import MetaTrader5 as mt5
from src.routes.dataMt5 import log_all_accounts_parallel
from src.controls.daily_email_sender import send_email_with_attachment
import asyncio

# Khởi tạo MT5 khi server khởi động
async def startup_mt5():
    # Bắt đầu background task
    asyncio.create_task(log_all_accounts_parallel())