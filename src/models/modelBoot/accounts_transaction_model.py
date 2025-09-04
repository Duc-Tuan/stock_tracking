from sqlalchemy import Column, Integer, String, Float
from src.models.model import Base, relationship

class AccountsBoot(Base):
    __tablename__ = "accounts_boot"

    id = Column(Integer, primary_key=True)
    username = Column(Integer)
    name = Column(String, nullable=False)
    balance = Column(Float, default=0)
    equity = Column(Float, default=0)
    margin = Column(Float, default=0)
    free_margin = Column(Float, default=0)
    leverage = Column(Integer, default=100)
    server = Column(String)
    loginId = Column(Integer)