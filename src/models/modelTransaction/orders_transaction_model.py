from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from src.models.model import Base, relationship
from datetime import datetime

class OrdersTransaction(Base):
    __tablename__ = "orders_transaction"  # Lưu các lệnh giao dịch gửi lên MT5

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts_transaction.username"), nullable=False)
    symbol = Column(String, ForeignKey("symbol_transaction.symbol"), nullable=False)
    order_type = Column(Enum('buy', 'sell'), nullable=False)
    volume = Column(Float, nullable=False) # khối lượng lệnh
    price = Column(Float, nullable=False) 
    sl = Column(Float) # Mức dừng lỗ (Stop Loss)
    tp = Column(Float) # Mức chốt lời (Take Profit)
    time = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum('pending', 'filled', 'cancelled', 'rejected'), default='pending')

    account = relationship("AccountsTransaction", back_populates="orders")
    symbol_rel = relationship("SymbolTransaction", back_populates="orders")