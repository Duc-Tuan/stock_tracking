from sqlalchemy import Column, Integer, String, Float
from src.models.model import Base, relationship

class SymbolTransaction(Base):
    __tablename__ = "symbol_transaction"

    symbol = Column(String, primary_key=True)
    description = Column(String)
    digits = Column(Integer, nullable=False)
    contract_size = Column(Float, default=100000)
    tick_size = Column(Float, default=0.0001)
    tick_value = Column(Float, default=1)
    swap_long = Column(Float, default=0)
    swap_short = Column(Float, default=0)

    orders = relationship("OrdersTransaction", back_populates="symbol_rel")
    positions = relationship("PositionTransaction", back_populates="symbol_rel")
    deals = relationship("DealTransaction", back_populates="symbol_rel")
    ticks = relationship("PriceTickTransaction", back_populates="symbol_rel")