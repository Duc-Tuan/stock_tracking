from fastapi import APIRouter, Depends, HTTPException, Query
from src.controls.authControll import get_current_user
from src.models.modelTransaction.schemas import SendOrderBootMonitorRequest, CloseOrderBoot
from src.controls.monitorBootControls.SendOrderControll import place_market_lot, get_order_monitor_boot, get_detail_order_boot, close_order_boot
from typing import List, Literal

router = APIRouter()

@router.post("/lot-monitor-boot")
def post_lot_transaction( data: List[SendOrderBootMonitorRequest], current_user: dict =Depends(get_current_user)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    
    try:
        message = place_market_lot(data, current_user.id)
        return {"status": "success", "message": message}
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)

@router.post("/close-monitor-boot")
def post_lot_transaction( data: CloseOrderBoot, current_user: dict =Depends(get_current_user)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    
    try:
        message = close_order_boot(data, current_user.id)
        return {"status": "success", "message": message}
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)
    
@router.get("/boot_monitor_order")
def post_boot_order(
    start_time: int = Query(None),
    end_time: int = Query(None),
    status: Literal["Buy", "Sell"] = Query(None),
    page: int = Query(1),
    limit: int = Query(10), 
    acc_transaction: int= Query(None), 
    current_user: dict =Depends(get_current_user)
):

    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    try:
        data = {
            "acc_transaction": acc_transaction,
            "start_time": start_time,
            "end_time": end_time,
            "status": status,
            "page": page,
            "limit": limit,
        }

        return get_order_monitor_boot(data, current_user.id)
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/boot_monitor_detail_order/{id}")
def post_boot_order(
    id: int, 
    current_user: dict =Depends(get_current_user)
):

    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    try:
        return get_detail_order_boot(id, current_user.id)
    except Exception as e:
        return {"status": "error", "message": str(e)}