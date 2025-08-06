from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from src.models.model import Base, relationship
from datetime import datetime

class DealTransaction(Base):
    __tablename__ = "deal_transaction"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts_transaction.id"), nullable=False)
    symbol = Column(String, ForeignKey("symbol_transaction.symbol"), nullable=False)
    position_type = Column(String, nullable=False)
    volume = Column(Float, nullable=False)
    open_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    open_time = Column(DateTime)
    close_time = Column(DateTime, default=datetime.utcnow)
    profit = Column(Float)
    swap = Column(Float, default=0)
    commission = Column(Float, default=0)
    comment = Column(Text)

    account = relationship("AccountsTransaction", back_populates="deals")
    symbol_rel = relationship("SymbolTransaction", back_populates="deals")