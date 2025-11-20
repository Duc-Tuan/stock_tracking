from sqlalchemy import Column, Integer, DateTime, Float, Boolean, ForeignKey
from src.models.model import Base
from datetime import datetime

class StatisticalBootBB(Base):
    __tablename__ = "statistical_boot_bb"

    id = Column(Integer, primary_key=True)
    boot_id_bb = Column(Integer, ForeignKey("info_boot_bb.id"))
    dd = Column(Float, default=0)
    volume = Column(Float, default=0)
    profit = Column(Float, default=0)
    time = Column(DateTime, default=datetime.now)
