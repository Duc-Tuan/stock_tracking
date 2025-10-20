from sqlalchemy import Column, Integer, DateTime, Enum
from src.models.model import Base, relationship
from datetime import datetime

class InfoLoTransactionBoot(Base):
    __tablename__ = "info_lo_transaction_boot"

    id = Column(Integer, primary_key=True)
    login_id = Column(Integer, nullable=False)
    acc_reference = Column(Integer, nullable=False)
    acc_reciprocal = Column(Integer, nullable=False)
    type = Column(Enum("CLOSE", "RUNNING"), default="RUNNING")
    time = Column(DateTime, default=datetime.now)