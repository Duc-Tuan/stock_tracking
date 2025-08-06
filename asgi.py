import uvicorn
import socketio
from mt5_api import app as fastapi_app, sio

# Mount socket.io vào FastAPI
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

if __name__ == "__main__":
    uvicorn.run("asgi:app", host="0.0.0.0", port=8000)
