from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from src.models.model import Base, relationship
from datetime import datetime

class OrdersTransaction(Base):
    __tablename__ = "orders_transaction"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts_transaction.id"), nullable=False)
    symbol = Column(String, ForeignKey("symbol_transaction.symbol"), nullable=False)
    order_type = Column(Enum('buy', 'sell', 'buy_limit', 'sell_limit', 'buy_stop', 'sell_stop'),nullable=False)  # 'buy_limit', 'sell_stop', etc.
    volume = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    sl = Column(Float)
    tp = Column(Float)
    time = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum('pending', 'filled', 'cancelled', 'rejected'), default='pending')  # 'pending', 'executed', 'cancelled'

    # account = relationship("accounts_transaction", back_populates="orders_transaction")
    account = relationship("AccountsTransaction", back_populates="orders")
    symbol_rel = relationship("SymbolTransaction", back_populates="orders")