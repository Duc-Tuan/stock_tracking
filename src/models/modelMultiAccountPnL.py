from sqlalchemy import Column, Integer, Float, DateTime, String, Index
from src.models.model import Base
from datetime import datetime

class MultiAccountPnL(Base):
    __tablename__ = "multi_account_pnl_logs"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(Integer, index=True)
    time = Column(DateTime, default=datetime.utcnow)
    total_pnl = Column(Float)
    num_positions = Column(Integer)
    by_symbol = Column(String)