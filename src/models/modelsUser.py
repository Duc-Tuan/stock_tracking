from sqlalchemy import Column, Integer, String, Enum
from src.models.model import Base, relationship
import enum

class UserRole(enum.Enum):
    admin = "admin"
    user = "user"
    viewer = "viewer"

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(Enum(UserRole), nullable=False)

    symbol_rel = relationship("SymbolTransaction", back_populates="user")
    deals = relationship("DealTransaction", back_populates="user")
    lotaccount = relationship("LotInformation", back_populates="user")
    positions = relationship("PositionTransaction", back_populates="user")

from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelTransaction.deal_transaction_model import DealTransaction
from src.models.modelTransaction.lot_information_model import LotInformation
from src.models.modelsUser import UserModel