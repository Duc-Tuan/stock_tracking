from fastapi import APIRouter, Depends, HTTPException, Query
from src.controls.authControll import get_current_user
from src.models.modelstatisticalPnl import StatisticalPNL
from sqlalchemy.orm import Session
from src.middlewares.authMiddleware import get_db
from fastapi.responses import ORJSONResponse
from sqlalchemy import func

from src.models.modelPNL import (
    MultiAccountPnL_M1, MultiAccountPnL_M5, MultiAccountPnL_M10, MultiAccountPnL_M15,
    MultiAccountPnL_M30, MultiAccountPnL_H1, MultiAccountPnL_H2, MultiAccountPnL_H4,
    MultiAccountPnL_H6, MultiAccountPnL_H8, MultiAccountPnL_H12, MultiAccountPnL_D,
    MultiAccountPnL_W, MultiAccountPnL_MN,
)

router = APIRouter()

# Mapping timeframe -> model
TIMEFRAME_MODEL_MAP = {
    "M1": MultiAccountPnL_M1,
    "M5": MultiAccountPnL_M5,
    "M10": MultiAccountPnL_M10,
    "M15": MultiAccountPnL_M15,
    "M30": MultiAccountPnL_M30,
    "H1": MultiAccountPnL_H1,
    "H2": MultiAccountPnL_H2,
    "H4": MultiAccountPnL_H4,
    "H6": MultiAccountPnL_H6,
    "H8": MultiAccountPnL_H8,
    "H12": MultiAccountPnL_H12,
    "D": MultiAccountPnL_D,
    "W": MultiAccountPnL_W,
    "MN": MultiAccountPnL_MN,
}

@router.get("/symbols", response_class=ORJSONResponse)
def get_symbols(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=30000),
    page: int = Query(1, ge=1),
    id_symbol: int = Query(..., ge=1),
    timeframe: str = Query("M1", pattern="^(M1|M5|M10|M15|M30|H1|H2|H4|H6|H8|H12|D|W|MN)$")
):
    # if str(current_user.role) != "UserRole.admin":
    #     raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập symbols")

    try:
        
        Model = TIMEFRAME_MODEL_MAP.get(timeframe)
        if not Model:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")

        # Phân trang
        offset = (page - 1) * limit

        # Lấy tổng số bản ghi
        total_count = db.query(func.count(Model.id)).filter(Model.login == id_symbol).scalar()

        # Query dữ liệu
        query = (
            db.query(Model)
            .filter(Model.login == id_symbol)
            .order_by(Model.time.desc())
            .offset(offset)
            .limit(limit)
        )

        data = query.all()

        # Tính toán trang cuối
        is_last_page = (offset + limit) >= total_count

        return ORJSONResponse(
            content={
                "timeframe": timeframe,
                "symbol_id": id_symbol,
                "page": page,
                "limit": limit,
                "is_last_page": is_last_page,
                "data": [
                    {
                        "id": row.id,
                        "login": row.login,
                        "time": row.time.isoformat() if row.time else None,
                        "open": row.open,
                        "high": row.high,
                        "low": row.low,
                        "close": row.close,
                        "P": row.P,
                    }
                    for row in data
                ],
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/statistical", response_class=ORJSONResponse)
def get_statistical(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    login_id: int = 0,
):
    # if str(current_user.role) != "UserRole.admin":
    #     raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập symbols")

    try:
        data = db.query(StatisticalPNL).filter(StatisticalPNL.login == login_id).all()

        result = []
        for row in data:
            r = row.__dict__.copy()
            r.pop("_sa_instance_state", None)
            result.append(r)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))