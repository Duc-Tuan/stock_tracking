from fastapi import APIRouter, Depends, HTTPException, Query
import MetaTrader5 as mt5
from src.controls.authControll import get_current_user
from src.models.modelMultiAccountPnL import MultiAccountPnL
from sqlalchemy.orm import Session
from src.middlewares.authMiddleware import get_db


router = APIRouter()

def get_symbols_db(db, page, limit, id_symbol):
    # Phân trang
    offset = (page - 1) * limit
    data = db.query(MultiAccountPnL).filter(MultiAccountPnL.login == id_symbol).order_by(MultiAccountPnL.time.desc()).offset(offset).limit(limit).distinct().all()
    return  data


@router.get("/symbols")
def get_symbols(current_user: dict =Depends(get_current_user), db: Session = Depends(get_db), page: int = Query(1, ge=1),limit: int = Query(20, ge=1, le=5000), id_symbol: int = Query(1, ge=1)):
    data = get_symbols_db(db, page, limit, id_symbol)
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập symbols")
    
    # Tổng số bản ghi 183455033
    total = db.query(MultiAccountPnL).filter(MultiAccountPnL.login == id_symbol).count()
    
    # Convert từng dòng (và loại bỏ login nếu cần)
    result = []
    for row in data:
        row_dict = row.__dict__.copy()
        row_dict.pop("_sa_instance_state", None)
        row_dict.pop("login", None)  # bỏ trường login nếu cần
        result.append(row_dict)

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": result
    }
    
