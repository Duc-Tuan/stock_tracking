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
    account_transaction_id: int
    price: float
    volume: float
    stop_loss: float
    take_profit: float
    status: Literal["Xuoi_Limit", "Nguoc_Limit", "Xuoi_Stop", "Nguoc_Stop", "Lenh_thi_truong"]
    type: Literal["CLOSE", "RUNNING"]
    by_symbol:  List[symbolItem]
    status_sl_tp: Literal["Xuoi_Limit", "Nguoc_Limit", "Xuoi_Stop", "Nguoc_Stop"]
    IsUSD: bool
    usd: int

class SettingRiskTransactionRequest(BaseModel):
    risk: float

class CloseFastLotItem(BaseModel):
    id: int

class CloseFastLotRequest(BaseModel):
    data: List[CloseFastLotItem] = []

class OrderData(BaseModel):
    price: float
    sl: float
    tp: float
    symbol: Literal["GBPUSD", "EURUSD", "XAUUSD", "USDJPY"]
    type: Literal[0, 1, 2, 3, 4, 5]
    volume: float

class OrderBootItem(BaseModel):
    username: int  
    data: OrderData
    type: Literal["EXNESS", "FUND"]

class CloseOrderBootItem(BaseModel):
    id: int
    serverName: int

class CloseOrderBoot(BaseModel):
    id: int

class getLots(BaseModel):
    start_time: int
    end_time: int
    status: Literal["Xuoi_Limit", "Nguoc_Limit", "Xuoi_Stop", "Nguoc_Stop", "Lenh_thi_truong"]
    acc_transaction: int
    page: int
    limit: int


class DeleteLotRequest(BaseModel):
    id: int

class PatchotRequest(BaseModel):
    id: int
    stop_loss: float
    take_profit: float


class DealTransactionSchema(BaseModel):
    id: int
    symbol: str
    volume: float
    profit: float
    open_time: datetime
    close_time: datetime
    position_type: str
    open_price: float
    close_price: float
    account_id: int

    class Config:
        from_attributes = True

class NotificationTransactionSchema(BaseModel):
    id: int
    loginId: int
    account_transaction_id: int
    isRead: bool
    is_send: bool
    symbol: str
    total_volume: float | None
    profit: float
    monney_acctransaction: float
    total_order: int
    risk: float
    type: str
    time: datetime
    daily_risk: float
    type_notification: Literal["daily", "risk"]

    # Trường mới: danh sách deal con
    deals: List[DealTransactionSchema] = []

    class Config:
        from_attributes = True

class OddOrderRequest(BaseModel):
    price: float | None
    id_notification: int
    symbol: str
    lot: float
    order_type: Literal["BUY", "SELL"]
    account_transaction_id: int
    lot_id: int

class CloseOddOrderRequest(BaseModel):
    ticket: int
    vloume: float
    acc_transaction: int

class NoteRequest(BaseModel):
    html: str