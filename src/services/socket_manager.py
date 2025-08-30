import socketio, asyncio
from socketio import AsyncRedisManager

# Redis URL (chạy redis-server trước)
redis_url = "redis://127.0.0.1:6379/0"

# Tạo server socket.io
mgr = AsyncRedisManager(redis_url)
sio = socketio.AsyncServer( client_manager=mgr, cors_allowed_origins='*', async_mode='asgi', compression=False)

def emit_sync(event: str, data):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(sio.emit(event, data))
        else:
            loop.run_until_complete(sio.emit(event, data))
    except RuntimeError:
        # Nếu chưa có event loop (vd: trong thread)
        asyncio.run(sio.emit(event, data))

def emit_chat_message_sync(listen: str, data):
    for item in data:
        symbol_id = item['login']
        room = f"chat_message_{symbol_id}"
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(sio.emit(listen, item, room=room))
            else:
                loop.run_until_complete(sio.emit(listen, item, room=room))
        except RuntimeError:
            asyncio.run(sio.emit(listen, item, room=room))