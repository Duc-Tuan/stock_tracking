from fastapi import APIRouter, Depends, HTTPException, Query
from src.controls.authControll import get_current_user
from src.controls.transaction_controls.notification_controll import setting_risk_acc_transaction_controll, get_setting_risk_acc_transaction_controll, setting_daily_risk_acc_transaction_controll, post_setting_daily_risk_acc_transaction_controll
from src.models.modelTransaction.schemas import SettingRiskTransactionRequest

router = APIRouter()

@router.post("/setting_risk")
def post_setting_risk_acc_transaction(data: SettingRiskTransactionRequest, current_user: dict =Depends(get_current_user)):

    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    
    try:
        return setting_risk_acc_transaction_controll(data)
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)
    
@router.get("/setting_risk")
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
        return get_setting_risk_acc_transaction_controll(data, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)
    
@router.post("/setting_daily_risk")
def post_setting_risk_acc_transaction(data: SettingRiskTransactionRequest, current_user: dict =Depends(get_current_user)):

    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    
    try:
        return post_setting_daily_risk_acc_transaction_controll(data)
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)
    
@router.get("/setting_daily_risk")
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
        return setting_daily_risk_acc_transaction_controll(data, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)