from datetime import datetime
from sqlalchemy import case, or_
from sqlalchemy.orm import aliased
from database import Context
from models.account import Account
from models.transaction import Transaction


class TransactionRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_by_idempotency_key(
        self,
        source_account_id: int,
        idempotency_key: str,
    ) -> Transaction | None:
        return (
            self.session.query(Transaction)
            .filter(
                Transaction.source_account_id == source_account_id,
                Transaction.idempotency_key == idempotency_key,
            )
            .first()
        )

    def count_source_transfers(self, source_account_id: int, period_start: datetime, period_end: datetime) -> int:
        return (
            self.session.query(Transaction)
            .filter(
                Transaction.source_account_id == source_account_id,
                Transaction.created_at >= period_start,
                Transaction.created_at < period_end,
            )
            .count()
        )

    def create(self, transaction: Transaction) -> Transaction:
        self.session.add(transaction)
        self.session.flush()
        return transaction

    def list_by_account(self, account_id: int, limit: int, offset: int,
                        start_date=None, end_date=None) -> list:
        source = aliased(Account)
        destination = aliased(Account)
        query = (
            self.session.query(
                Transaction,
                case(
                    (Transaction.source_account_id == account_id, destination.account_key),
                    else_=source.account_key,
                ).label("counterparty_account_key"),
            )
            .join(source, source.id == Transaction.source_account_id)
            .join(destination, destination.id == Transaction.destination_account_id)
            .filter(or_(Transaction.source_account_id == account_id,
                        Transaction.destination_account_id == account_id))
        )
        if start_date is not None:
            query = query.filter(Transaction.created_at >= start_date)
        if end_date is not None:
            query = query.filter(Transaction.created_at < end_date)
        return query.order_by(Transaction.created_at.desc(), Transaction.id.desc()).limit(limit).offset(offset).all()

    def count_by_account(self, account_id: int, start_date=None, end_date=None) -> int:
        query = self.session.query(Transaction).filter(
            or_(Transaction.source_account_id == account_id,
                Transaction.destination_account_id == account_id)
        )
        if start_date is not None:
            query = query.filter(Transaction.created_at >= start_date)
        if end_date is not None:
            query = query.filter(Transaction.created_at < end_date)
        return query.count()
