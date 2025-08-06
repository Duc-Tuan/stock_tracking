from sqlalchemy import Column, Integer, String, Float
from src.models.model import Base, relationship

class AccountsTransaction(Base):
    __tablename__ = "accounts_transaction"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    balance = Column(Float, default=0)
    equity = Column(Float, default=0)
    margin = Column(Float, default=0)
    free_margin = Column(Float, default=0)
    leverage = Column(Integer, default=100)

    orders = relationship("OrdersTransaction", back_populates="account")
    positions = relationship("PositionTransaction", back_populates="account")
    deals = relationship("DealTransaction", back_populates="account")