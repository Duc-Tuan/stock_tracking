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
