from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from src.models.model import Base, relationship
from datetime import datetime

class PositionTransaction(Base):
    __tablename__ = "position_transaction" # Ghi nhận các vị thế (position) đang mở

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts_transaction.username"), nullable=False)
    symbol = Column(String, ForeignKey("symbol_transaction.symbol"), nullable=False)
    position_type = Column(String, nullable=False)  # 'buy', 'sell'
    volume = Column(Float, nullable=False)
    open_price = Column(Float, nullable=False)
    sl = Column(Float)
    tp = Column(Float)
    open_time = Column(DateTime, default=datetime.utcnow)
    swap = Column(Float, default=0)
    commission = Column(Float, default=0)
    magic_number = Column(Integer) #Dùng để phân biệt lệnh theo bot EA (Expert Advisor)
    comment = Column(Text)

    account = relationship("AccountsTransaction", back_populates="positions")
    symbol_rel = relationship("SymbolTransaction", back_populates="positions")

from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction