from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from src.models.model import Base, relationship
from datetime import datetime

class DealTransaction(Base):
    __tablename__ = "deal_transaction" # Lưu thông tin giao dịch đã thực hiện

    id = Column(Integer, primary_key=True)
    username_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts_transaction.username"), nullable=False)
    symbol = Column(String, ForeignKey("symbol_transaction.symbol"), nullable=False)
    position_type = Column(String, nullable=False) #Loại vị thế: buy hoặc sell
    volume = Column(Float, nullable=False)
    open_price = Column(Float, nullable=False) #Giá mở giao dịch
    close_price = Column(Float, nullable=False) #Giá đóng giao dịch
    open_time = Column(DateTime) #Thời gian mở giao dịch
    close_time = Column(DateTime, default=datetime.utcnow) #Thời gian đóng giao dịch
    profit = Column(Float) #Lợi nhuận hoặc thua lỗ từ giao dịch
    swap = Column(Float, default=0)
    commission = Column(Float, default=0) #Phí hoa hồng
    comment = Column(Text) #Ghi chú hoặc mô tả thêm từ giao dịch

    account = relationship("AccountsTransaction", back_populates="deals")
    symbol_rel = relationship("SymbolTransaction", back_populates="deals")
    user = relationship("UserModel", back_populates="deals")

from src.models.modelTransaction.accounts_transaction_model import AccountsTransaction
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelsUser import UserModel
