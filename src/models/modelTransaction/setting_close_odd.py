from sqlalchemy import Column, Integer, DateTime, Boolean, String, Float
from src.models.model import Base, relationship
from datetime import datetime

class SettingCloseOddTransaction(Base):
    __tablename__ = "setting_close_odd" # Tài khoản giao dịch trên MT5

    id = Column(Integer, primary_key=True)
    loginId = Column(Integer)
    risk = Column(Integer, default=0)
    time = Column(DateTime, default=datetime.utcnow)