from fastapi import APIRouter, Depends, HTTPException, Query
import MetaTrader5 as mt5
from src.controls.authControll import get_current_user
from src.models.modelMultiAccountPnL import MultiAccountPnL
from sqlalchemy.orm import Session
from src.middlewares.authMiddleware import get_db
from sqlalchemy import func

router = APIRouter()

@router.get("/symbols")
def get_symbols(current_user: dict =Depends(get_current_user), 
                db: Session = Depends(get_db), 
                page: int = Query(1, ge=1),
                limit: int = Query(20, ge=1, le=5000), 
                id_symbol: int = Query(1, ge=1)):
    
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập symbols")
    
    try: 

        # Nếu có last_time thì lấy dữ liệu nhỏ hơn thời điểm đó
        # last_time: Optional[str] = Query(None, description="ISO datetime của record cuối cùng trang trước"),
        # if last_time:
        #     query = query.filter(MultiAccountPnL.time < last_time)

        # # Sắp xếp và giới hạn
        # data = query.order_by(MultiAccountPnL.time.desc()).limit(limit).all()

        # Lấy cursor mới
        # next_cursor = result[-1]["time"] if result else None

        # Truy vấn nhanh nhờ index
        offset = (page - 1) * limit
        data = (
            db.query(MultiAccountPnL)
            .filter(MultiAccountPnL.login == id_symbol)
            .order_by(MultiAccountPnL.time.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        # Chuyển sang dict, bỏ cột login
        result = [
            {k: v for k, v in row.__dict__.items() if k not in ["_sa_instance_state", "login"]}
            for row in data
        ]

        total = db.query(func.count(MultiAccountPnL.id)).filter(
            MultiAccountPnL.login == id_symbol
        ).scalar()
        
    except Exception as e:
        db.rollback()
    finally:
        db.close()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": result
    }
    
