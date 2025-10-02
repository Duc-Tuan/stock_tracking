from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Boolean
from src.models.model import Base, relationship
from datetime import datetime

class SymbolTransaction(Base):
    __tablename__ = "symbol_transaction" # Thông tin cặp tiền giao dịch

    id = Column(Integer, primary_key=True)
    id_transaction = Column(Integer)
    username_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lot_information.id"), nullable=False)
    account_transaction_id = Column(Integer, ForeignKey("accounts_transaction.username"), nullable=False)
    symbol = Column(String)
    description = Column(String)
    digits = Column(Integer, nullable=False)
    contract_size = Column(Float, default=100000)
    tick_size = Column(Float, default=0.0001)
    tick_value = Column(Float, default=1)
    swap_long = Column(Float, default=0)
    swap_short = Column(Float, default=0)
    price_open = Column(Float, default=0)
    price_transaction = Column(Float, default=0)
    volume = Column(Float, default=0)
    profit = Column(Float, default=0)
    status = Column(Enum('pending', 'filled', 'cancelled', 'rejected'), default='pending')
    type = Column(Enum('BUY', 'SELL'), default='BUY')
    time = Column(DateTime, default=datetime.utcnow)
    is_odd = Column(Boolean, default=False)

    positions = relationship("PositionTransaction", back_populates="symbol_rel")
    deals = relationship("DealTransaction", back_populates="symbol_rel")
    ticks = relationship("PriceTickTransaction", back_populates="symbol_rel")
    lotaccount = relationship("LotInformation", back_populates="symbol_rel")
    account = relationship("AccountsTransaction", back_populates="symbol_rel")
    user = relationship("UserModel", back_populates="symbol_rel")

from src.models.modelTransaction.position_transaction_model import PositionTransaction
from src.models.modelTransaction.deal_transaction_model import DealTransaction
from src.models.modelTransaction.lot_information_model import LotInformation
from src.models.modelTransaction.priceTick_transaction_model import PriceTickTransaction
from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction
from src.models.modelsUser import UserModel