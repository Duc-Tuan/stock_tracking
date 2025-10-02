from fastapi import APIRouter, Depends, HTTPException, Query
from src.controls.authControll import get_current_user
from src.controls.transaction_controls.notification_controll import get_notification_controll, post_notification_read, get_detail_notification_read
from src.models.modelTransaction.schemas import CloseFastLotRequest
from src.models.modelTransaction.schemas import NotificationTransactionSchema

router = APIRouter()
    
@router.get("/notifcations")
def set_position_transaction( 
    start_time: int = Query(None),
    end_time: int = Query(None),
    page: int = Query(1),
    limit: int = Query(10), 
    current_user: dict =Depends(get_current_user)):

    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    
    try:
        data = {
            "start_time": start_time,
            "end_time": end_time,
            "page": page,
            "limit": limit,
        }
        return get_notification_controll(data, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)

@router.post("/notifcations_read")
def set_position_transaction( 
    data: CloseFastLotRequest,
    current_user: dict =Depends(get_current_user)):

    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    
    try:
        return post_notification_read(data, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)

@router.get("/notifcations_read/{id}", response_model=NotificationTransactionSchema)
def set_position_transaction( 
    id: int,   # lấy id từ URL param
    current_user: dict = Depends(get_current_user)):

    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    
    try:
        return get_detail_notification_read(id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)