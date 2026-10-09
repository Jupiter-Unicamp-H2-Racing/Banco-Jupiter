from datetime import datetime
from database import Context
from models.transaction import Transaction


class TransactionRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

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
