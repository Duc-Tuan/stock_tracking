from sqlalchemy import Column, Integer, Enum, Float, ForeignKey, DateTime,Boolean
from src.models.model import Base, relationship
from datetime import datetime

class LotInformation(Base):
    __tablename__ = "lot_information" # Thông tin đặt lệnh

    id = Column(Integer, primary_key=True)
    username_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    boot_id_bb = Column(Integer, ForeignKey("info_boot_bb.id"))
    account_monitor_id = Column(Integer, ForeignKey("acc_mt5.username"), nullable=False)
    account_transaction_id = Column(Integer, ForeignKey("accounts_transaction.username"), nullable=False)
    price = Column(Float)
    volume = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    time = Column(DateTime, default=datetime.now)
    status = Column(Enum("Xuoi_Limit", "Nguoc_Limit", "Xuoi_Stop", "Nguoc_Stop", "Lenh_thi_truong"), default='Lenh_thi_truong') 
    type = Column(Enum("CLOSE", "RUNNING"), default="RUNNING")
    status_sl_tp = Column(Enum("Xuoi_Limit", "Nguoc_Limit", "Xuoi_Stop", "Nguoc_Stop"), default='Xuoi_Limit')
    
    IsUSD = Column(Boolean, default=False)
    usd = Column(Integer, default=0)

    account = relationship("AccountsTransaction", back_populates="lotaccount")
    symbol_rel = relationship("SymbolTransaction", back_populates="lotaccount")
    user = relationship("UserModel", back_populates="lotaccount")

from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelsUser import UserModel