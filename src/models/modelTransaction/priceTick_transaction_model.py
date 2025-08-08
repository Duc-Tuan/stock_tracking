from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from src.models.model import Base, relationship
from datetime import datetime

class PriceTickTransaction(Base):
    __tablename__ = "priceTick_transaction" #Ghi nhận lịch sử giá (tick)

    id = Column(Integer, primary_key=True)
    symbol = Column(String, ForeignKey("symbol_transaction.symbol"), nullable=False)
    bid = Column(Float, nullable=False) #Giá mua tại thời điểm tick (giá mà trader có thể bán)
    ask = Column(Float, nullable=False) #Giá bán tại thời điểm tick (giá mà trader có thể mua)
    time = Column(DateTime, default=datetime.utcnow)

    symbol_rel = relationship("SymbolTransaction", back_populates="ticks")