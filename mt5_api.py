from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime

from src.models.model import Base, engine
from src.routes.authRouter import router as auth_router
from src.routes.accMt5Router import router as auth_mt5_router
from src.routes.downloadFileRouter import router as download_router
from src.routes.symbolRouter import router as symbol_router
import socketio
from src.routes.wsRouter import websocket_pnl_io
from fastapi.encoders import jsonable_encoder
import asyncio
from urllib.parse import parse_qs
from src.utils.stop import stopDef

# Tạo server Socket.IO
sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')
socket_app = socketio.ASGIApp(sio)

app = FastAPI()

load_dotenv()
Base.metadata.create_all(bind=engine)

# Cho phép CORS nếu frontend gọi từ domain khác (JS client)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Thay bằng domain cụ thể nếu cần
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn route login
app.include_router(auth_router)

# Gắn route login mt
app.include_router(auth_mt5_router)

# Gắn route download file
app.include_router(download_router)

# Import sau khi tạo sio để tránh circular import
@sio.event
async def connect(sid, data):
    await sio.emit('message', {'data': 'Welcome!'}, to=sid)

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    
@sio.event
async def connect(sid, environ):
    query_params = parse_qs(environ.get('QUERY_STRING', ''))
    symbol_id = query_params.get('symbol_id', [None])[0]
    token = query_params.get('token', [None])[0]
    sio.start_background_task(send_data_periodically, sid, symbol_id, token)

async def send_data_periodically(sid, symbol_id, token):
    while True:
        if stopDef(datetime.now()):
            await asyncio.sleep(60)
            continue

        await asyncio.sleep(5)
        dataNew = websocket_pnl_io(symbol_id, token)
        await sio.emit('chat_message', jsonable_encoder(dataNew), to=sid)

#w /symbols
app.include_router(symbol_router)

# Mount socket.io vào FastAPI
app = socketio.ASGIApp(sio, other_asgi_app=app)

# venv\Scripts\activate
# chạy app: uvicorn mt5_api:app --reload