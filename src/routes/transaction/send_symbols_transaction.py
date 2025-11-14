from fastapi import APIRouter, Depends, HTTPException, Query
from src.controls.authControll import get_current_user
from src.controls.transaction_controls.all_send_symbols_controlls import get_all_send_symbols
from typing import Literal

router = APIRouter()

@router.get("/all-send-symbols")
def set_all_send_symbol_transaction( 
    start_time: int = Query(None),
    end_time: int = Query(None),
    page: int = Query(1),
    limit: int = Query(10), 
    acc_transaction: int= Query(None),
    symbol: str= Query(None),
    status: Literal['pending', 'filled', 'cancelled', 'rejected'] = Query(None),
    type: Literal['BUY', 'SELL'] = Query(None),
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
            "status": status,
            "type": type,
            "symbol": symbol,
        }
        return get_all_send_symbols(data, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)