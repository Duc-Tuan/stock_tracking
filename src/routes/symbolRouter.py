from fastapi import APIRouter, Depends, HTTPException, Query
import MetaTrader5 as mt5
from src.controls.authControll import get_current_user
from src.models.modelMultiAccountPnL import MultiAccountPnL
from sqlalchemy.orm import Session
from src.middlewares.authMiddleware import get_db
from fastapi.responses import ORJSONResponse

router = APIRouter()

@router.get("/symbols", response_class=ORJSONResponse)
def get_symbols(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=10000),
    id_symbol: int = Query(..., ge=1),
    last_id: int = None
):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập symbols")

    try:
        # chọn cột trừ login, by_symbol
        columns = [
            c for c in MultiAccountPnL.__table__.columns
            if c.name not in ("login", "by_symbol", "num_positions")
        ]

        query = db.query(*columns).filter(MultiAccountPnL.login == id_symbol)

        # Nếu có cursor thì chỉ lấy record nhỏ hơn id đó
        if last_id:
            query = query.filter(MultiAccountPnL.id < last_id)

        data = (
            query
            .order_by(MultiAccountPnL.id.desc())   # Dùng id thay cho time
            .limit(limit + 1)                      # Lấy dư 1 record để check has_more
            .all()
        )

        has_more = len(data) > limit
        if has_more:
            data = data[:limit]

        result = [dict(row._mapping) for row in data]

        # Cursor mới (dùng record cuối cùng trong page này)
        next_cursor = result[-1]["id"] if result else None

        return {
            "limit": limit,
            "has_more": has_more,
            "next_cursor": next_cursor,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))