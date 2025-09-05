from typing import List
from fastapi import APIRouter, Depends, HTTPException
from src.controls.authControll import get_current_user
from src.models.modelTransaction.schemas import CloseFastLotRequest, OrderBootItem, CloseOrderBootItem
from src.controls.transaction_controls.close_fast_lo_contronls import close_fast_lot_contronlls, send_order_boot, close_order_boot

router = APIRouter()

@router.post("/close-fast-lot")
def post_lot_transaction( data: CloseFastLotRequest, current_user: dict =Depends(get_current_user)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    try:
        message = close_fast_lot_contronlls(data.data, current_user.id)
        return {"status": "success", "message": message}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/boot_order")
def post_boot_order( data: List[OrderBootItem], current_user: dict =Depends(get_current_user)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    try:
        message = send_order_boot(data)
        return {"status": "success", "message": message}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/boot_close_order")
def post_boot_order( data: List[CloseOrderBootItem], current_user: dict =Depends(get_current_user)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    try:
        message = close_order_boot(data)
        return {"status": "success", "message": message}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
