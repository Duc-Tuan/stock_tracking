from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from src.controls.authControll import get_current_user
from src.middlewares.authMiddleware import get_db
from sqlalchemy.orm import Session
from src.models.modelMultiAccountPnL import MultiAccountPnL
from src.models.modelTransaction.position_transaction_model import PositionTransaction
from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction
from src.models.model import SessionLocal
from sqlalchemy import func
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
            "by_symbol": data.by_symbol,
            "id_symbol": id_symbol
        }
    except Exception as e:
        print("❌ Lỗi lưu DB:", e)
    finally:
        db.close()
    
def websocket_position_io(id_symbol: int = "", token: str = ""):
    user = get_current_user(token)
    if str(user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập position")
    
    db = SessionLocal()
    try:
        data = db.query(PositionTransaction).filter(
            PositionTransaction.username_id == user.id
        ).order_by(PositionTransaction.time.desc()).all()

        query = db.query(AccountsTransaction).filter(AccountsTransaction.loginId == user.id).order_by(AccountsTransaction.id.desc()).all()

        return {
            "position": data,
            "acc": query
        }
    except Exception as e:
        print("❌ Lỗi lưu DB:", e)
    finally:
        db.close()

def websocket_acc_transaction_io(id_symbol: int = "", token: str = ""):
    user = get_current_user(token)
    if str(user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập acc")
    
    db = SessionLocal()
    try:
        query = (
            db.query(
                AccountsTransaction,
                func.count(PositionTransaction.id).label("position")
            )
            .outerjoin(PositionTransaction, PositionTransaction.account_id == AccountsTransaction.username)
            .filter(AccountsTransaction.loginId == user.id)
            .group_by(AccountsTransaction.id)
            .order_by(AccountsTransaction.id.desc())
        )

        result = []
        for acc, position in query.all():
            acc_dict = acc.__dict__.copy()
            acc_dict["position"] = position
            result.append(acc_dict)

        return result
    except Exception as e:
        print("❌ Lỗi lưu DB:", e)
    finally:
        db.close()
    
