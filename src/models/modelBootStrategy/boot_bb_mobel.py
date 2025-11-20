from sqlalchemy import Column, Integer, DateTime, Float, Boolean, Enum
from src.models.model import Base
from datetime import datetime
import enum

class BootBB(enum.Enum):
    M1 = "M1"
    M5 = "M5"
    M10 = "M10"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H2 = "H2"
    H4 = "H4"
    H6 = "H6"
    H8 = "H8"
    H12 = "H12"
    D = "D"
    W = "W"
    MN = "MN"

class BootBB(Base):
    __tablename__ = "info_boot_bb"

    id = Column(Integer, primary_key=True)
    bb1 = Column(Float, default=0)
    bb2 = Column(Float, default=0)
    period = Column(Float, default=0)
    acc_monitor = Column(Integer, default=0)
    acc_transaction = Column(Integer, default=0)
    volume_start = Column(Float, default=0)
    entry_point = Column(Float, default=0)
    rsi_upper = Column(Float, default=0)
    rsi_low = Column(Float, default=0)
    rsi_period = Column(Integer, default=0)
    start = Column(Boolean, default=True)
    profit_close = Column(Float, default=0)
    TF = Column(Enum(BootBB), nullable=False)
    time = Column(DateTime, default=datetime.now)