from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime
from src.models.model import Base

# Bảng log PnL
class PnLLog(Base):
    __tablename__ = "pnl_logs"

    id = Column(Integer, primary_key=True, index=True)
    time = Column(DateTime, default=datetime.utcnow)
    total_pnl = Column(Float)
    by_symbol = Column(String)  # Lưu dạng JSON string
    symbols=Column(String)
