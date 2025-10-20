from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from src.models.model import Base, relationship
from datetime import datetime

class OrdersBoot(Base):
    __tablename__ = "orders_boot"

    id = Column(Integer, primary_key=True)
    id_transaction = Column(Integer, default=0)
    lo_boot_id = Column(Integer)
    user_id = Column(Integer)
    account_id = Column(Integer, ForeignKey("accounts_transaction.username"), nullable=False)
    symbol = Column(String, nullable=False)
    order_type = Column(Integer, nullable=False)
    volume = Column(Float, nullable=False)
    price = Column(Float, nullable=False) 
    price_market = Column(Float, nullable=False) 
    sl = Column(Float)
    tp = Column(Float)
    profit = Column(Integer, default=0)
    time = Column(DateTime, default=datetime.now)
    status = Column(Enum('pending', 'filled', 'cancelled', 'rejected'), default='pending')
    type_acc = Column(Enum('EXNESS', 'FUND'), default='EXNESS')