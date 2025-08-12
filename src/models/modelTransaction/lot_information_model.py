from sqlalchemy import Column, Integer, Enum, Float, ForeignKey, DateTime
from src.models.model import Base, relationship
from datetime import datetime

class LotInformation(Base):
    __tablename__ = "lot_information" # Thông tin đặt lệnh

    id = Column(Integer, primary_key=True)
    account_monitor_id = Column(Integer, ForeignKey("acc_mt5.username"), nullable=False)
    account_transaction_id = Column(Integer, ForeignKey("accounts_transaction.username"), nullable=False)
    price = Column(Float)
    volume = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    time = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum("Xuoi_Limit", "Nguoc_Limit", "Xuoi_Stop", "Nguoc_Stop", "Lenh_thi_truong"), default='Lenh_thi_truong') 
    type = Column(Enum("CLOSE", "RUNNING"), default="RUNNING")

    accMt5 = relationship("AccountMt5", back_populates="lotaccount")
    account = relationship("AccountsTransaction", back_populates="lotaccount")
    symbol_rel = relationship("SymbolTransaction", back_populates="lotaccount")