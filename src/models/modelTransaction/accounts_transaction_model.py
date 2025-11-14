from sqlalchemy import Column, Integer, String, Float, Enum
from src.models.model import Base, relationship
from src.models.modelDecentralization.modelUser import user_acc_transaction_association

class AccountsTransaction(Base):
    __tablename__ = "accounts_transaction" # Tài khoản giao dịch trên MT5

    id = Column(Integer, primary_key=True)
    username = Column(Integer)
    # account_monitor_id = Column(Integer, ForeignKey("acc_mt5.username"), nullable=False)
    name = Column(String, nullable=False)
    balance = Column(Float, default=0)
    equity = Column(Float, default=0)
    margin = Column(Float, default=0)
    free_margin = Column(Float, default=0)
    leverage = Column(Integer, default=100)
    server = Column(String)
    loginId = Column(Integer)

    id_setting_close_odd = Column(Integer, default=0) 
    id_setting_close_odd_daily_risk = Column(Integer, default=0) 
    type_acc = Column(Enum("QUY", "USD", "COPY", "DEPOSIT", "RECIPROCAL",  "COM", "SWWING" ,"VAY", "DEMO", "RECIPROCAL_ACC"), default='QUY') 
    monney_acc = Column(Integer, default=0)

    users = relationship("UserModel", secondary=user_acc_transaction_association, back_populates="accountsTransaction")

    orders = relationship("OrdersTransaction", back_populates="account")
    positions = relationship("PositionTransaction", back_populates="account")
    deals = relationship("DealTransaction", back_populates="account")
    lotaccount = relationship("LotInformation", back_populates="account")
    symbol_rel = relationship("SymbolTransaction", back_populates="account")
    notification = relationship("NotificationTransaction", back_populates="account")
    # monitor_account_mt5 = relationship("AccountMt5", back_populates="account")

from src.models.modelTransaction.orders_transaction_model import OrdersTransaction
from src.models.modelTransaction.position_transaction_model import PositionTransaction
from src.models.modelTransaction.deal_transaction_model import DealTransaction
from src.models.modelTransaction.lot_information_model import LotInformation
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelTransaction.notification_transansaction import NotificationTransaction