from fastapi import APIRouter, Depends, HTTPException, Query
from src.middlewares.authMiddleware import get_db
from sqlalchemy.orm import Session
from src.controls.authControll import get_current_user
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction

router = APIRouter()

def get_symbols_db(db, page, limit, id_symbol):
    # Phân trang
    offset = (page - 1) * limit
    data = db.query(SymbolTransaction).filter(SymbolTransaction.username_id == id_symbol).order_by(SymbolTransaction.time.desc()).offset(offset).limit(limit).distinct().all()
    return  data

@router.get("/symbol-transaction")
def get_orders(current_user: dict =Depends(get_current_user), db: Session = Depends(get_db), page: int = Query(1, ge=1),limit: int = Query(20, ge=1, le=20)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập symbols")
    
    data = get_symbols_db(db, page, limit, current_user.id)

    total = db.query(SymbolTransaction).filter(SymbolTransaction.username_id == current_user.id).count()

    return {
        "data": data,
        "total": total,
        "page": page,
        "limit": limit,
    }