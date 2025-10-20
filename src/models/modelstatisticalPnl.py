from sqlalchemy import Column, Integer, Float, DateTime, String, Date
from src.models.model import Base
from datetime import datetime

class StatisticalPNL(Base):
    __tablename__ = "statistical_pnl"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(Integer, index=True)
    time = Column(DateTime, default=datetime.now)

    # best/worst day
    best_day = Column(Date)
    best_day_change = Column(Float)
    worst_day = Column(Date)
    worst_day_change = Column(Float)

    # best/worst week
    best_week = Column(String)               # YYYY-WW
    best_week_change = Column(Float)
    worst_week = Column(String)
    worst_week_change = Column(Float)

    # best/worst month
    best_month = Column(String)              # YYYY-MM
    best_month_change = Column(Float)
    worst_month = Column(String)
    worst_month_change = Column(Float)

    # tracking min/max (để không cần query lại)
    day_min = Column(Float, default=0.0)
    day_max = Column(Float, default=0.0)
    week_min = Column(Float, default=0.0)
    week_max = Column(Float, default=0.0)
    month_min = Column(Float, default=0.0)
    month_max = Column(Float, default=0.0)