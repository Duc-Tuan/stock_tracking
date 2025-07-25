import MetaTrader5 as mt5
from src.routes.savePnl import run_save_pnl
import asyncio

# Khởi tạo MT5 khi server khởi động
async def startup_mt5():
    # Bắt đầu background task
    asyncio.create_task(run_save_pnl())