from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from src.models.model import Base, relationship
from datetime import datetime

class PositionBoot(Base):
    __tablename__ = "position_boot" # Ghi nhận các vị thế (position) đang mở

    id = Column(Integer, primary_key=True)
    id_transaction = Column(Integer, nullable=False)
    username = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    position_type = Column(String, nullable=False)  # 'buy', 'sell'
    volume = Column(Float, nullable=False)
    open_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    sl = Column(Float)
    tp = Column(Float)
    open_time = Column(DateTime, default=datetime.utcnow)
    time = Column(DateTime, default=datetime.utcnow)
    swap = Column(Float, default=0)
    profit = Column(Float, default=0)
    commission = Column(Float, default=0)
    magic_number = Column(Integer) #Dùng để phân biệt lệnh theo bot EA (Expert Advisor)
    comment = Column(Text)