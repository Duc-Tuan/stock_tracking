import MetaTrader5 as mt5
from src.routes.savePnl import run_save_pnl, run_save_pnl_blocking
import asyncio

# Khởi tạo MT5 khi server khởi động
async def startup_mt5():
    # Bắt đầu background task
    # asyncio.create_task(run_save_pnl())
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_save_pnl_blocking)