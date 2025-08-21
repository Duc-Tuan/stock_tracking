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

    # account = relationship("AccountsTransaction", back_populates="monitor_account_mt5")

# from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction