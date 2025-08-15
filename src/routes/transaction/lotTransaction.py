from fastapi import APIRouter, Depends, HTTPException, Query
from src.middlewares.authMiddleware import get_db
from sqlalchemy.orm import Session
from src.controls.authControll import get_current_user
from src.models.modelTransaction.schemas import SymbolTransactionRequest, getLots
from src.controls.transaction_controls.place_market_lot import place_market_lot, get_symbols_db
from typing import Literal

router = APIRouter()

@router.get("/lots-transaction")
def post_lot_transaction( 
    start_time: int = Query(None),
    end_time: int = Query(None),
    status: Literal["Xuoi_Limit", "Nguoc_Limit", "Xuoi_Stop", "Nguoc_Stop", "Lenh_thi_truong"] = Query(None),
    page: int = Query(1),
    limit: int = Query(10), 
    acc_transaction: int= Query(None),
    current_user: dict =Depends(get_current_user)):

    # if str(current_user.role) != "UserRole.admin":
    #     raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập symbols")
    try:
        data = {
            "acc_transaction": acc_transaction,
            "start_time": start_time,
            "end_time": end_time,
            "status": status,
            "page": page,
            "limit": limit,
        }
        return get_symbols_db(data, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)

@router.post("/lot-transaction")
def post_lot_transaction( data: SymbolTransactionRequest, current_user: dict =Depends(get_current_user)):
    # if str(current_user.role) != "UserRole.admin":
    #     raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập symbols")
    try:
        message = place_market_lot(data, current_user.id)
        return {"status": "success", "message": message}
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)
    
