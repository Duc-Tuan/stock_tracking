import MetaTrader5 as mt5
from fastapi import APIRouter, Depends, HTTPException
from src.models.modelTransaction.schemas import OddOrderRequest, CloseOddOrderRequest
from src.models.modelTransaction.notification_transansaction import NotificationTransaction
from src.controls.authControll import get_current_user
from src.controls.transaction_controls.place_market_lot import order_send_mt5, close_position_transaction_controll
from src.services.terminals_transaction import terminals_transaction
from src.models.model import SessionLocal

router = APIRouter()

# Khởi tạo MT5 1 lần khi app start
def mt5_connect(account_name: int):
    acc = terminals_transaction[str(account_name)]
    # Đóng kết nối cũ nếu đang mở
    mt5.shutdown()
    # Kết nối mới
    if not mt5.initialize(path=acc['path']):
        raise Exception(f"Không connect được MT5 {account_name}. Lỗi: {mt5.last_error()}")
    return True
    
@router.post("/odd_order")
def set_position_transaction( 
    data: OddOrderRequest,
    current_user: dict = Depends(get_current_user)):

    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    
    try:
        db = SessionLocal()
        mt5_connect(data.account_transaction_id)

        isCheck = db.query(NotificationTransaction).filter(
            NotificationTransaction.id == data.id_notification
        ).first()

        if isCheck:
            isCheck.is_send = True

        data = order_send_mt5(
            is_odd= True,
            price=data.price,
            symbol=data.symbol,
            lot=data.lot,
            order_type=data.order_type,
            usename_id=current_user.id,
            lot_id=data.lot_id,
            account_transaction_id=data.account_transaction_id
        )

        if (data['data']):
            symbolSQL, order_transaction = data['data']
            db.add(symbolSQL)
            db.add(order_transaction)
        db.commit()
        return {"status": "succes", "mess": "Gửi lệnh thị trường thành công"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=403, detail=e)
    finally:
        db.close()
        mt5.shutdown()

@router.post("/close_odd_order")
def close_position_transaction( 
    data: CloseOddOrderRequest,
    current_user: dict = Depends(get_current_user)):

    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    
    try:
        mt5_connect(data.acc_transaction)
        return close_position_transaction_controll(
            ticket= data.ticket,
            volume= data.vloume,
            loginId= current_user.id,
            acc_transaction= data.acc_transaction
        )
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)
    finally:
        mt5.shutdown()