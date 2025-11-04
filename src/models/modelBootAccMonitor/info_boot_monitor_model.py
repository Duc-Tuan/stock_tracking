from sqlalchemy import Column, Integer, DateTime, Enum, Float
from src.models.model import Base, relationship
from datetime import datetime

class InfoBootMonitorBoot(Base):
    __tablename__ = "info_boot_monitor_boot"

    id = Column(Integer, primary_key=True)
    login_id = Column(Integer, nullable=False)

    acc_reference = Column(Integer, nullable=False) # tham chiếu
    acc_reciprocal = Column(Integer, nullable=False) # đối ứng

    type_acc_reference = Column(Enum("XUOI", "NGUOC"), default="XUOI")
    type_acc_reciprocal = Column(Enum("XUOI", "NGUOC"), default="XUOI")

    type = Column(Enum("CLOSE", "RUNNING"), default="RUNNING")

    tp_acc_reference = Column(Float, nullable=False) # tham chiếu
    tp_acc_reciprocal = Column(Float, nullable=False) # tham chiếu

    volume = Column(Float, nullable=False)
    acc_monitor = Column(Integer, nullable=False)
    time = Column(DateTime, default=datetime.now)