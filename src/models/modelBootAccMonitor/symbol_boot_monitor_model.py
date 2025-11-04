from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Boolean
from src.models.model import Base, relationship
from datetime import datetime

class SymbolMonitorBoot(Base):
    __tablename__ = "symbol_monitor_boot" # Thông tin cặp tiền giao dịch

    id = Column(Integer, primary_key=True)
    id_transaction = Column(Integer)
    username_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("info_boot_monitor_boot.id"), nullable=False)
    account_transaction_id = Column(Integer, ForeignKey("accounts_transaction.username"), nullable=False)
    symbol = Column(String)
    description = Column(String)
    digits = Column(Integer, nullable=False)
    contract_size = Column(Float, default=100000)
    tick_size = Column(Float, default=0.0001)
    tick_value = Column(Float, default=1)
    swap_long = Column(Float, default=0)
    swap_short = Column(Float, default=0)
    price_open = Column(Float, default=0)
    volume = Column(Float, default=0)
    profit = Column(Float, default=0)
    status = Column(Enum('pending', 'filled', 'cancelled', 'rejected'), default='pending')
    type = Column(Enum('BUY', 'SELL'), default='BUY')
    time = Column(DateTime, default=datetime.utcnow)