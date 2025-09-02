# venv\Scripts\activate

<!-- D:\mt5\stock_tracking\py_bridge -->

<!-- Mở server để đồng bộ socket cho 3 tiến trình -->
# C:\Users\Duc Tuan\Downloads\Redis-x64-5.0.14.1>redis-server.exe

<!-- Tiến trình chạy theo dõi pnl, vào/đóng lệnh -->
# python src/services/mt5.py
# python src/services/monitor_transaction.py

# uvicorn asgi:app --host 0.0.0.0 --port 8000 
<!-- --workers 6 -->