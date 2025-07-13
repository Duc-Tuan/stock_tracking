import MetaTrader5 as mt5
from src.routes.dataMt5 import log_all_accounts_parallel
from src.controls.daily_email_sender import run_schedule_email
import asyncio

# Khởi tạo MT5 khi server khởi động
async def startup_mt5():
    # Bắt đầu background task
    asyncio.create_task(log_all_accounts_parallel())
    asyncio.create_task(run_schedule_email())