import asyncio
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime
from urllib.parse import parse_qs
from fastapi.encoders import jsonable_encoder

from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelTransaction.deal_transaction_model import DealTransaction
from src.models.modelTransaction.orders_transaction_model import OrdersTransaction
from src.models.modelTransaction.position_transaction_model import PositionTransaction
from src.models.modelTransaction.priceTick_transaction_model import PriceTickTransaction
from src.models.modelSwapMt5 import SwapMt5

from src.models.model import Base, engine
from src.routes.authRouter import router as auth_router
from src.routes.accMt5Router import router as auth_mt5_router
from src.routes.downloadFileRouter import router as download_router
from src.routes.symbolRouter import router as symbol_router
from src.routes.transaction.trading import router as trading_router
from src.routes.wsRouter import websocket_pnl_io
from src.utils.stop import stopDef

# Load env
load_dotenv()

# SQLAlchemy init
Base.metadata.create_all(bind=engine)

# Tạo FastAPI app
app = FastAPI()

# Cho phép CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký route HTTP
app.include_router(auth_router)
app.include_router(auth_mt5_router)
app.include_router(download_router)
app.include_router(symbol_router)

app.include_router(trading_router)

# Tạo server socket.io
sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')

# Lưu task theo client ID
active_tasks = {}

# Gửi data định kỳ
async def send_data_periodically(sid, symbol_id, token):
    try:
        while True:
            if stopDef(datetime.now()):
                await asyncio.sleep(60)
                continue

            await asyncio.sleep(5)
            try:
                dataNew = await asyncio.wait_for(
                    asyncio.to_thread(websocket_pnl_io, symbol_id, token),
                    timeout=3.0
                )
                await sio.emit('chat_message', jsonable_encoder(dataNew), to=sid)
            except Exception as e:
                print(f"[ERROR] send_data_periodically: {e}")

    except asyncio.CancelledError:
        print(f"⛔ Task for sid={sid} cancelled")

@sio.event
async def connect(sid, environ):
    print(f"✅ Client connected: {sid}")
    query_params = parse_qs(environ.get('QUERY_STRING', ''))
    symbol_id = query_params.get('symbol_id', [None])[0]
    token = query_params.get('token', [None])[0]

    task = sio.start_background_task(send_data_periodically, sid, symbol_id, token)
    active_tasks[sid] = task

@sio.event
async def disconnect(sid):
    print(f"❌ Client disconnected: {sid}")
    task = active_tasks.pop(sid, None)
    if task:
        task.cancel()
