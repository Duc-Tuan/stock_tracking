from fastapi import APIRouter, Depends, HTTPException, Query
from src.middlewares.authMiddleware import get_db
from sqlalchemy.orm import Session
from src.controls.authControll import get_current_user
from src.models.modelTransaction.schemas import SymbolTransactionRequest
from src.controls.transaction_controls.place_market_lot import place_market_lot

router = APIRouter()

@router.post("/lot-transaction")
def post_lot_transaction( data: SymbolTransactionRequest, current_user: dict =Depends(get_current_user)):
    # if str(current_user.role) != "UserRole.admin":
    #     raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập symbols")
    try:
        message = place_market_lot(data, current_user.id)
        return {"status": "success", "message": message}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
