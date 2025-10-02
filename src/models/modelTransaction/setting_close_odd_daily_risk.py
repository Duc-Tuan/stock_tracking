from sqlalchemy import Column, Integer, DateTime, Boolean, String, Float
from src.models.model import Base, relationship
from datetime import datetime

class SettingCloseOddDailyRiskTransaction(Base):
    __tablename__ = "setting_close_odd_daily_risk" # Tài khoản giao dịch trên MT5

    id = Column(Integer, primary_key=True)
    loginId = Column(Integer)
    risk = Column(Integer, default=0)
    time = Column(DateTime, default=datetime.utcnow)