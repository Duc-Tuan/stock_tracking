from fastapi import APIRouter, Depends, HTTPException, Query
from src.middlewares.authMiddleware import get_db
from sqlalchemy.orm import Session
from src.controls.authControll import get_current_user
from src.models.modelTransaction.schemas import CloseFastLotRequest
from src.controls.transaction_controls.close_fast_lo_contronls import close_fast_lot_contronlls

router = APIRouter()

@router.post("/close-fast-lot")
def post_lot_transaction( data: CloseFastLotRequest, current_user: dict =Depends(get_current_user)):
    # if str(current_user.role) != "UserRole.admin":
    #     raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập symbols")
    try:
        message = close_fast_lot_contronlls(data.data, current_user.id)
        return {"status": "success", "message": message}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
