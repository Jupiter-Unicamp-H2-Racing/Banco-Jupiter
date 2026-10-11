from sqlalchemy import (
    BigInteger, CHAR, CheckConstraint, Column, DateTime,
    ForeignKey, Index, String, UniqueConstraint, desc, func,
)
from models.base import Base


class Transaction(Base):
    __tablename__ = "transaction"

    id = Column(BigInteger, primary_key=True)
    transaction_key = Column(CHAR(36), nullable=False, unique=True)
    idempotency_key = Column(String(255), nullable=True)
    source_account_id = Column(BigInteger, ForeignKey("account.id"), nullable=False)
    destination_account_id = Column(BigInteger, ForeignKey("account.id"), nullable=False)
    amount = Column(BigInteger, nullable=False)
    fee_amount = Column(BigInteger, nullable=False, default=0, server_default="0")
    fee_account_id = Column(BigInteger, ForeignKey("account.id"), nullable=True)
    kind = Column(String(16), nullable=False, default="transfer", server_default="transfer")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
    UniqueConstraint( "source_account_id","idempotency_key",name="uq_transaction_source_idempotency",),
        CheckConstraint("amount > 0", name="ck_transaction_amount_positive"),
        CheckConstraint("fee_amount >= 0", name="ck_transaction_fee_nonnegative"),
        CheckConstraint("kind IN ('transfer', 'deposit', 'fee')", name="ck_transaction_kind"),
        CheckConstraint("source_account_id <> destination_account_id", name="ck_transaction_accounts_different"),
        Index("ix_transaction_source_created_at", "source_account_id", desc("created_at"), desc("id")),
        Index("ix_transaction_destination_created_at", "destination_account_id", desc("created_at"), desc("id")),
    )
