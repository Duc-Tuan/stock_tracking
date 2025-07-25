from sqlalchemy import Column, Integer, Float, DateTime, String
from src.models.model import Base
from datetime import datetime, timedelta

class AccountMt5(Base):
    __tablename__ = "acc_mt5"

    id = Column(Integer, primary_key=True, index=True)
    loginId = Column(Integer)
    username = Column(Integer)
    password = Column(String)
    server = Column(String)
    by_symbol = Column(String)