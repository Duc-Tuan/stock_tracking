from sqlalchemy import Column, Integer, Enum, Float, ForeignKey, DateTime
from src.models.model import Base, relationship
from datetime import datetime

class OrderInformation(Base):
    __tablename__ = "order_information" # Tài khoản giao dịch trên MT5

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts_transaction.username"), nullable=False)
    price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    time = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum('pending', 'filled', 'cancelled', 'rejected'), default='pending') 

    account = relationship("AccountsTransaction", back_populates="username")