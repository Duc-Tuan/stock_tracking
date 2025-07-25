from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Enum
from src.models.model import Base

class UserToken(Base):
    __tablename__ = "user_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.now())
    device_id = Column(String, nullable=False)  # ✅ mới
