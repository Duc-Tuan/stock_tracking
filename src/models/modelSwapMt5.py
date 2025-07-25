from sqlalchemy import Column, Integer, Float, DateTime, String
from src.models.model import Base
from datetime import datetime, timedelta

class SwapMt5(Base):
    __tablename__ = "swap_mt5"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(Integer)
    server = Column(String)
    swap = Column(Float)
    created_at = Column(DateTime, default=(datetime.utcnow() + timedelta(hours=7)))