import asyncio
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from urllib.parse import parse_qs
from fastapi.encoders import jsonable_encoder
from collections import defaultdict

from src.models.model import Base, engine
from src.routes.authRouter import router as auth_router
from src.routes.accMt5Router import router as auth_mt5_router
from src.routes.downloadFileRouter import router as download_router
from src.routes.symbolRouter import router as symbol_router
from src.routes.transaction.trading import router as trading_router
from src.routes.transaction.lotTransaction import router as lot_router
from src.routes.transaction.close_fast_lot import router as close_lot_router
from src.routes.transaction.orderTransaction import router as order_close_router
from src.routes.transaction.send_symbols_transaction import router as send_symbol_router
from src.routes.transaction.position_transaction import router as position_transaction_router
from src.routes.wsRouter import websocket_pnl_io, websocket_position_io

# Load env
load_dotenv()

# SQLAlchemy init
from src.models.modelTransaction import *
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

app.include_router(lot_router)
app.include_router(trading_router)
app.include_router(close_lot_router)
app.include_router(order_close_router)
app.include_router(send_symbol_router)
app.include_router(position_transaction_router)

# Tạo server socket.io
sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi', compression=False)

symbol_clients = defaultdict(set)
symbol_last_data = {}
symbol_tasks = {}

async def broadcast_symbol_data(symbol_id, token):
    try:
        while True:
            try:
                data = await asyncio.to_thread(websocket_pnl_io, symbol_id, token)
                symbol_last_data[symbol_id] = data
                for sid in list(symbol_clients[symbol_id]):
                    await sio.emit('chat_message', jsonable_encoder(data), to=sid)
            except Exception as e:
                print(f"[ERROR] broadcast_symbol_data: {e}")
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print(f"⛔ Task for symbol {symbol_id} cancelled")

async def broadcast_order_data(symbol_id, token):
    try:
        while True:
            try:
                data = await asyncio.to_thread(websocket_position_io, symbol_id, token)
                symbol_last_data[symbol_id] = data
                for sid in list(symbol_clients[symbol_id]):
                    await sio.emit('position_message', jsonable_encoder(data), to=sid)
            except Exception as e:
                print(f"[ERROR] broadcast_symbol_data: {e}")
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print(f"⛔ Task for symbol {symbol_id} cancelled")

@sio.event
async def connect(sid, environ):
    query = parse_qs(environ.get('QUERY_STRING', ''))
    symbol_id = query.get('symbol_id', [None])[0]
    token = query.get('token', [None])[0]
    
    symbol_clients[symbol_id].add(sid)
    
    if symbol_id not in symbol_tasks:
        print(f"🚀 Starting task for symbol {symbol_id}")
        pnl_task = asyncio.create_task(broadcast_symbol_data(symbol_id, token))

        order_task = asyncio.create_task(broadcast_order_data(symbol_id, token))
        symbol_tasks[symbol_id] = [pnl_task, order_task]

@sio.event
async def disconnect(sid):
    print(f"❌ Client disconnected: {sid}")
    for symbol_id, clients in list(symbol_clients.items()):
        if sid in clients:
            clients.remove(sid)
            if not clients:
                print(f"🛑 Stopping tasks for symbol {symbol_id}")
                tasks = symbol_tasks.pop(symbol_id, [])
                for task in tasks:
                    if task:
                        task.cancel()
