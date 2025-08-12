from sqlalchemy import Column, Integer, String
from src.models.model import Base, relationship

class AccountMt5(Base):
    __tablename__ = "acc_mt5"

    id = Column(Integer, primary_key=True, index=True)
    loginId = Column(Integer)
    username = Column(Integer)
    password = Column(String)
    server = Column(String)
    by_symbol = Column(String)

    lotaccount = relationship("LotInformation", back_populates="accMt5")