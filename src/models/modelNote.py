from sqlalchemy import Column, Integer, Text
from src.models.model import Base

class Note(Base):
    __tablename__ = "note"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(Integer, index=True)
    html = Column(Text)  # dùng TEXT để lưu HTML dài