from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from src.models.model import Base, relationship
from datetime import datetime

class OrdersTransaction(Base):
    __tablename__ = "orders_transaction"  # Lưu các lệnh giao dịch gửi lên MT5

    id = Column(Integer, primary_key=True)
    id_transaction = Column(Integer)
    account_id = Column(Integer, ForeignKey("accounts_transaction.username"), nullable=False)
    symbol = Column(String, nullable=False)
    order_type = Column(Enum('BUY', 'SELL'), nullable=False)
    volume = Column(Float, nullable=False) # khối lượng lệnh
    price = Column(Float, nullable=False) 
    sl = Column(Float) # Mức dừng lỗ (Stop Loss)
    tp = Column(Float) # Mức chốt lời (Take Profit)
    time = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum('pending', 'filled', 'cancelled', 'rejected'), default='pending')

    account = relationship("AccountsTransaction", back_populates="orders")

from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction