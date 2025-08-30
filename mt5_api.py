import asyncio
from fastapi import FastAPI, HTTPException
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
from src.services.socket_manager import sio
from src.controls.authControll import get_current_user
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

symbol_clients = defaultdict(set)

@sio.event
async def connect(sid, environ):
    query = parse_qs(environ.get('QUERY_STRING', ''))
    symbol_id = query.get('symbol_id', [None])[0]
    token = query.get('token', [None])[0]

    symbol_clients[symbol_id].add(sid)

    user = get_current_user(token)
    if str(user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập socket")
    
    if symbol_id:
        # Lưu vào room để sau này emit riêng
        # await sio.enter_room(sid, f"position_message_{user.id}")
        await sio.enter_room(sid, f"chat_message_{symbol_id}")

@sio.event
async def disconnect(sid):
    print(f"❌ Client disconnected: {sid}")
    for symbol_id, clients in list(symbol_clients.items()):
        if sid in clients:
            clients.remove(sid)
            if not clients:
                print(f"🛑 Stopping tasks for symbol {symbol_id}")
