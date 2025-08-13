from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Literal

from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelTransaction.deal_transaction_model import DealTransaction
from src.models.modelTransaction.orders_transaction_model import OrdersTransaction
from src.models.modelTransaction.position_transaction_model import PositionTransaction
from src.models.modelTransaction.priceTick_transaction_model import PriceTickTransaction

class OrderOut(BaseModel):
    id: int
    account_id: int
    symbol: str
    order_type: str
    volume: float
    price: float
    sl: Optional[float]
    tp: Optional[float]
    status: str
    time: datetime

    class Config:
        from_attributes = True


class PositionOut(BaseModel):
    id: int
    account_id: int
    symbol: str
    position_type: str
    volume: float
    open_price: float
    sl: Optional[float]
    tp: Optional[float]
    open_time: datetime
    swap: float
    commission: float
    comment: Optional[str]

    class Config:
        from_attributes = True

class ClosePositionRequest(BaseModel):
    position_id: int
    close_price: float

class OrderItem(BaseModel):
    symbol: str
    lot: float
    slippage: int
    type: Literal["buy", "sell", "buy_limit", "sell_limit", "buy_stop", "sell_stop"]  # hoặc tùy bạn

class OrderRequest(BaseModel):
    orders: List[OrderItem]

class symbolItem(BaseModel):
    current_price: float
    symbol: str
    type: str

class SymbolTransactionRequest(BaseModel):
    account_monitor_id: float
    account_transaction_id: float
    price: float
    volume: float
    stop_loss: float
    take_profit: float
    status: Literal["Xuoi_Limit", "Nguoc_Limit", "Xuoi_Stop", "Nguoc_Stop", "Lenh_thi_truong"]
    type: Literal["CLOSE", "RUNNING"]
    by_symbol:  List[symbolItem]
    status_sl_tp: Literal["Xuoi", "Nguoc"]