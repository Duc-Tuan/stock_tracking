from src.models.modelTransaction.schemas import OrderOut, PositionOut, ClosePositionRequest
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from src.models.modelTransaction.orders_transaction_model import OrdersTransaction
from src.models.modelTransaction.position_transaction_model import PositionTransaction
from src.middlewares.authMiddleware import get_db
from sqlalchemy.orm import Session
from src.models.modelTransaction.schemas import OrderRequest
from src.controls.transaction_controls.place_market_order import place_market_order
from concurrent.futures import ThreadPoolExecutor, as_completed

router = APIRouter()

@router.get("/orders", response_model=List[OrderOut])
def get_orders(db: Session = Depends(get_db)):
    return db.query(OrdersTransaction).all()

@router.get("/positions", response_model=List[PositionOut])
def get_positions(db: Session = Depends(get_db)):
    return db.query(PositionTransaction).all()

@router.post("/order/market")
def send_order(data: OrderRequest):
    results = []

    def run_order(order):
        try:
            message = place_market_order(
                symbol=order.symbol,
                lot=order.lot,
                slippage=order.slippage,
                order_type=order.type
            )
            return {"symbol": order.symbol, "status": "success", "message": message}
        except Exception as e:
            return {"symbol": order.symbol, "status": "error", "message": str(e)}

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_order, order) for order in data.orders]
        for future in as_completed(futures):
            results.append(future.result())

    return results
