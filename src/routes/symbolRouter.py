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
    last_id: int = None,
    # timeframe: str = Query("1H", regex="^(1H|2H|4H|1D|1W|MN)$")
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
    
        # # --- bucket theo timeframe ---
        # if timeframe.endswith("H"):
        #     hours = int(timeframe[:-1])
        #     bucket = func.date_trunc("hour", MultiAccountPnL.time) + func.make_interval(
        #         hours=(extract("hour", MultiAccountPnL.time) / hours).cast(Integer) * hours
        #     )
        # elif timeframe == "1D":
        #     bucket_normal = (
        #         func.date_trunc("day", MultiAccountPnL.time - func.make_interval(hours=7))
        #         + func.make_interval(hours=7)
        #     )
        #     case_bucket = case(
        #         (
        #             and_(
        #                 extract("dow", MultiAccountPnL.time) == 1,  # Monday
        #                 extract("hour", MultiAccountPnL.time).between(4, 6)
        #             ),
        #             func.date_trunc("day", MultiAccountPnL.time) + func.make_interval(hours=4)
        #         ),
        #         else_=bucket_normal
        #     )
        #     bucket = case_bucket
        # elif timeframe == "MN":
        #     bucket = func.date_trunc("month", MultiAccountPnL.time)
        # else:
        #     raise HTTPException(status_code=400, detail="Timeframe không hỗ trợ")

        # # --- subquery OHLC ---
        # subq = (
        #     db.query(
        #         bucket.label("bucket"),
        #         func.min(MultiAccountPnL.id).label("open_id"),
        #         func.max(MultiAccountPnL.id).label("close_id"),
        #         func.max(MultiAccountPnL.total_pnl).label("high"),
        #         func.min(MultiAccountPnL.total_pnl).label("low"),
        #         func.count().label("P")
        #     )
        #     .filter(MultiAccountPnL.login == id_symbol)
        # )

        # # Nếu có cursor thì chỉ lấy bucket < last_time
        # if last_time:
        #     subq = subq.filter(bucket < last_time)

        # subq = subq.group_by(bucket).order_by(bucket.desc()).limit(limit + 1).subquery()

        # # --- Join để lấy open/close ---
        # open_alias = aliased(MultiAccountPnL)
        # close_alias = aliased(MultiAccountPnL)

        # rows = (
        #     db.query(
        #         subq.c.bucket,
        #         open_alias.total_pnl.label("open"),
        #         close_alias.total_pnl.label("close"),
        #         subq.c.high,
        #         subq.c.low,
        #         subq.c.P
        #     )
        #     .join(open_alias, open_alias.id == subq.c.open_id)
        #     .join(close_alias, close_alias.id == subq.c.close_id)
        #     .order_by(subq.c.bucket.desc())
        #     .all()
        # )

        # # Check has_more
        # has_more = len(rows) > limit
        # if has_more:
        #     rows = rows[:limit]

        # result = [
        #     {
        #         "time": int(row.bucket.timestamp()),
        #         "open": row.open,
        #         "high": row.high,
        #         "low": row.low,
        #         "close": row.close,
        #         "P": row.P,
        #     }
        #     for row in rows
        # ]

        # # Cursor mới (bucket cuối)
        # next_cursor = result[-1]["time"] if result else None

        # return {
        #     "limit": limit,
        #     "has_more": has_more,
        #     "next_cursor": next_cursor,
        #     "data": result,
        # }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))