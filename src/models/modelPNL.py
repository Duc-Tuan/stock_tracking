from sqlalchemy import Column, Integer, Float, DateTime, String
from src.models.model import Base
from datetime import datetime

class PnLBase:
    id = Column(Integer, primary_key=True, index=True)
    login = Column(Integer, index=True)
    time = Column(DateTime, default=datetime.utcnow)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    P = Column(Float)  # JSON string hoặc symbol info

# Dynamic table factory
def create_pnl_class(name, table_name):
    return type(name, (PnLBase, Base), {'__tablename__': table_name})

# Khởi tạo các model
# phút
MultiAccountPnL_M1 = create_pnl_class('MultiAccountPnL_M1', 'multi_account_pnl_m1')
MultiAccountPnL_M5 = create_pnl_class('MultiAccountPnL_M5', 'multi_account_pnl_m5')
MultiAccountPnL_M10 = create_pnl_class('MultiAccountPnL_M10', 'multi_account_pnl_m10')
MultiAccountPnL_M15 = create_pnl_class('MultiAccountPnL_M15', 'multi_account_pnl_m15')
MultiAccountPnL_M30 = create_pnl_class('MultiAccountPnL_M30', 'multi_account_pnl_m30')

# Giờ
MultiAccountPnL_H1 = create_pnl_class('MultiAccountPnL_H1', 'multi_account_pnl_h1')
MultiAccountPnL_H2 = create_pnl_class('MultiAccountPnL_H2', 'multi_account_pnl_h2')
MultiAccountPnL_H4 = create_pnl_class('MultiAccountPnL_H4', 'multi_account_pnl_h4')
MultiAccountPnL_H6 = create_pnl_class('MultiAccountPnL_H6', 'multi_account_pnl_h6')
MultiAccountPnL_H8 = create_pnl_class('MultiAccountPnL_H8', 'multi_account_pnl_h8')
MultiAccountPnL_H12 = create_pnl_class('MultiAccountPnL_H12', 'multi_account_pnl_h12')

# Ngày
MultiAccountPnL_D = create_pnl_class('MultiAccountPnL_D', 'multi_account_pnl_d')

# Tuần
MultiAccountPnL_W = create_pnl_class('MultiAccountPnL_W', 'multi_account_pnl_w')

# Tháng
MultiAccountPnL_MN = create_pnl_class('MultiAccountPnL_MN', 'multi_account_pnl_mn')
