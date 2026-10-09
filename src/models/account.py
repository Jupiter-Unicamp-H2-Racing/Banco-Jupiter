from sqlalchemy import BigInteger, CHAR, CheckConstraint, Column, DateTime, Integer, String, func
from models.base import Base


class Account(Base):
    __tablename__ = "account"

    id = Column(BigInteger, primary_key=True)
    account_key = Column(CHAR(36), nullable=False, unique=True)
    balance = Column(BigInteger, nullable=False, default=0)
    tier_code = Column(String(20), nullable=False, default="STANDARD", server_default="STANDARD")
    monthly_free_transfers_limit = Column(Integer, nullable=False, default=5, server_default="5")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_account_balance_nonnegative"),
        CheckConstraint("monthly_free_transfers_limit >= 0", name="ck_account_free_limit_nonnegative"),
    )
