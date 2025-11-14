from fastapi import APIRouter, Depends, HTTPException, Query
from src.controls.authControll import get_current_admin
from src.models.modelsUser import UserModel
from sqlalchemy.orm import Session
from src.middlewares.authMiddleware import get_db
from fastapi.responses import ORJSONResponse
from sqlalchemy import func
from src.models.modelDecentralization.modelUser import user_mt5_association, user_acc_transaction_association
from src.models.modelTransaction.schemas import CloseFastLotItem


router = APIRouter()

@router.get("/user_all", response_class=ORJSONResponse)
def get_symbols(
    search: str | None = None,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=30000),
    page: int = Query(1, ge=1),
):
    try:
        # Phân trang
        offset = (page - 1) * limit

        # Base query không có search
        query = db.query(UserModel).filter(UserModel.id != 1)

        # Nếu có search -> thêm filter
        if search and search.strip():
            query = query.filter(UserModel.username.ilike(f"%{search}%"))

        # Lấy tổng số bản ghi
        total_count = query.count()

        # Query dữ liệu
        queryAll = (
            query
            .order_by(UserModel.id.desc())
            .offset(offset)
            .limit(limit)
        )

        data = queryAll.all()

        # Tính toán trang cuối
        is_last_page = (offset + limit) >= total_count

        result = []
        for row in data:
            isCheckViewAccMonitor = db.query(user_mt5_association).filter(
                user_mt5_association.c.user_id == row.id,
            ).all()

            isCheckViewAccTransaction = db.query(user_acc_transaction_association).filter(
                user_acc_transaction_association.c.user_id == row.id,
            ).all()

            item = {
                "id": row.id,
                "username": row.username,
                "role":  row.role,
                "isMonitor": len(isCheckViewAccMonitor),
                "isTransaction": len(isCheckViewAccTransaction)
            }
            result.append(item)

        return ORJSONResponse(
            content={
                "page": page,
                "limit": limit,
                "total": total_count,
                "is_last_page": is_last_page,
                "data": result,
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/detail_user/{id}", response_class=ORJSONResponse)
def assign_account_to_user(
    id: int,
    current_admin: UserModel = Depends(get_current_admin),
    db: Session = Depends(get_db)):
    try:
        user = db.query(UserModel).filter(UserModel.id == id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User không tồn tại")

        isCheckViewAccMonitor = db.query(user_mt5_association.c.id, user_mt5_association.c.account_mt5_id).filter(
            user_mt5_association.c.user_id == user.id,
        ).all()

        isCheckViewAccTransaction = db.query(user_acc_transaction_association.c.id,user_acc_transaction_association.c.acc_transaction_id).filter(
            user_acc_transaction_association.c.user_id == user.id,
        ).all()
        
        # Convert Row -> dict
        monitor_list = [dict(row._mapping) for row in isCheckViewAccMonitor]
        transaction_list = [dict(row._mapping) for row in isCheckViewAccTransaction]

        return ORJSONResponse(
            content={
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "viewAccMonitor": monitor_list,
                "viewAccTransaction": transaction_list,
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))