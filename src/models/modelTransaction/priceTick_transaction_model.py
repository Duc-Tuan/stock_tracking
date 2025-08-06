from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from src.models.model import Base, relationship
from datetime import datetime

class PriceTickTransaction(Base):
    __tablename__ = "priceTick_transaction"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, ForeignKey("symbol_transaction.symbol"), nullable=False)
    bid = Column(Float, nullable=False)
    ask = Column(Float, nullable=False)
    time = Column(DateTime, default=datetime.utcnow)

    symbol_rel = relationship("SymbolTransaction", back_populates="ticks")