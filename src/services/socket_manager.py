import socketio

# Tạo server socket.io
sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi', compression=False)