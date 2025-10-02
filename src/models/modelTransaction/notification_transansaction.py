from sqlalchemy import Column, Integer, DateTime, Boolean, String, Float, ForeignKey, Enum
from src.models.model import Base, relationship
from datetime import datetime

class NotificationTransaction(Base):
    __tablename__ = "notification_transansaction" # Tài khoản giao dịch trên MT5

    id = Column(Integer, primary_key=True)
    loginId = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_transaction_id = Column(Integer, ForeignKey("accounts_transaction.username"), nullable=False)
    isRead = Column(Boolean, default=False)
    symbol = Column(String, nullable=False)
    total_volume = Column(Float)
    is_send = Column(Boolean, default=False)
    profit = Column(Integer)
    total_order = Column(Integer)
    monney_acctransaction = Column(Integer)
    risk = Column(Integer)
    daily_risk = Column(Integer)
    type_notification = Column(Enum('daily', 'risk'), default='daily')
    type = Column(Enum('BUY', 'SELL'), default='BUY')
    time = Column(DateTime, default=datetime.utcnow)

    account = relationship("AccountsTransaction", back_populates="notification")
    deals = relationship("DealTransaction", back_populates="notification")

    def to_dict(self):
        return {
            "id": self.id,
            "loginId": self.loginId,
            "account_transaction_id": self.account_transaction_id,
            "symbol": self.symbol,
            "total_volume": self.total_volume,
            "profit": self.profit,
            "total_order": self.total_order,
            "risk": self.risk,
            "is_send": self.is_send,
            "isRead": self.isRead,
            "type": self.type,
            "time": self.time.isoformat() if self.time else None,
            "daily_risk": self.daily_risk,
            "type_notification": self.type_notification,
        }

from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction
from src.models.modelTransaction.deal_transaction_model import DealTransaction