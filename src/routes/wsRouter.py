from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from src.controls.authControll import get_current_user
from src.middlewares.authMiddleware import get_db
from sqlalchemy.orm import Session
from src.models.modelMultiAccountPnL import MultiAccountPnL
from src.models.model import SessionLocal
from datetime import datetime
import asyncio

router = APIRouter()

@router.websocket("/ws/pnl")
async def websocket_pnl(websocket: WebSocket, current_user: dict =Depends(get_current_user), db: Session = Depends(get_db), id_symbol: int = Query(1, ge=1)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập symbols")
    await websocket.accept()

    try:
        while True:
            data = db.query(MultiAccountPnL).filter(MultiAccountPnL.login == id_symbol).order_by(MultiAccountPnL.time.desc()).first()
            print(f"{data}")
            await websocket.send_json({
                "num_positions": 13142
            })

            await asyncio.sleep(1)
  # giữ kết nối và gửi dữ liệu định kỳ
    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        db.close()
    
def websocket_pnl_io(id_symbol: int = "", token: str = ""):
    if str(get_current_user(token).role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập symbols")
    
    db = SessionLocal()
    try:
        data = db.query(MultiAccountPnL).filter(MultiAccountPnL.login == id_symbol).order_by(MultiAccountPnL.time.desc()).first()
        return {
            "time": data.time,
            "total_pnl": data.total_pnl,
        }
    except Exception as e:
        print("❌ Lỗi lưu DB:", e)
    finally:
        db.close()
    
