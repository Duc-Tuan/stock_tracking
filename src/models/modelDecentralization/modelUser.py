from sqlalchemy import Table, Column, Integer, ForeignKey
from src.models.model import Base

user_mt5_association = Table(
    "user_mt5_association",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),  # khóa chính tự tăng
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE")),
    Column("account_mt5_id", Integer, ForeignKey("acc_mt5.id", ondelete="CASCADE")),
)

user_acc_transaction_association = Table(
    "user_acc_transaction_association",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),  # khóa chính tự tăng
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE")),
    Column("acc_transaction_id", Integer, ForeignKey("accounts_transaction.id", ondelete="CASCADE")),
)