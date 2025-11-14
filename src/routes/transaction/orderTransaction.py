from fastapi import APIRouter, Depends, HTTPException, Query
from src.middlewares.authMiddleware import get_db
from sqlalchemy.orm import Session
from src.controls.authControll import get_current_user
from src.controls.transaction_controls.order_close_controlls import get_order_close
from typing import Literal

router = APIRouter()

@router.get("/orders-close")
def get_order_close_transaction( 
    start_time: int = Query(None),
    end_time: int = Query(None),
    page: int = Query(1),
    limit: int = Query(10), 
    acc_transaction: int= Query(None),
    symbol: str= Query(None),
    current_user: dict =Depends(get_current_user)):

    # if str(current_user.role) != "UserRole.admin":
    #     raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    
    try:
        data = {
            "acc_transaction": acc_transaction,
            "start_time": start_time,
            "end_time": end_time,
            "page": page,
            "limit": limit,
            "symbol": symbol,
        }
        return get_order_close(data, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)