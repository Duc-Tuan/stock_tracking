from sqlalchemy import Column, Integer, String
from src.models.model import Base, relationship
from src.models.modelDecentralization.modelUser import user_mt5_association

class AccountMt5(Base):
    __tablename__ = "acc_mt5"

    id = Column(Integer, primary_key=True, index=True)
    loginId = Column(Integer)
    username = Column(Integer)
    password = Column(String)
    server = Column(String)
    by_symbol = Column(String)

    users = relationship("UserModel", secondary=user_mt5_association, back_populates="accounts")