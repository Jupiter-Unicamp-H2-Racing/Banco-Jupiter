from datetime import datetime, timezone
from uuid import uuid4

from controllers.base_controller import BaseController
from dtos.transaction_dto import TransactionDTO
from errors.custom_errors import (
    AccountNotFound,
    InsufficientBalance,
    InvalidTransfer,
)
from models.transaction import Transaction
from repositories.account_repository import AccountRepository
from repositories.transaction_repository import TransactionRepository

from utils.transaction_fee import (
    DEFAULT_MONTHLY_FREE_TRANSFERS_LIMIT,
    calculate_fee,
)

class TransactionController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.transaction_repository = TransactionRepository(self.context)

    def create(self, source_account_key: str, payload: dict) -> dict:
        amount = payload["amount"]
        destination_key = payload["destination_account_key"]

        try:
            # Resolve both public keys, then lock both rows in ascending primary-key
            # order. This prevents opposite-direction transfers from locking A->B
            # and B->A in conflicting orders.
            source_ref = self.account_repository.get_by_key(source_account_key)
            if source_ref is None:
                raise AccountNotFound(source_account_key)

            destination_ref = self.account_repository.get_by_key(destination_key)
            if destination_ref is None:
                raise AccountNotFound(destination_key)
            if source_ref.id == destination_ref.id:
                raise InvalidTransfer("Transfers to the same account are not allowed.")

            locked = {}
            for account_id in sorted((source_ref.id, destination_ref.id)):
                locked_account = self.account_repository.get_by_id_for_update(account_id)
                if locked_account is None:
                    missing_key = source_account_key if account_id == source_ref.id else destination_key
                    raise AccountNotFound(missing_key)
                locked[account_id] = locked_account

            source = locked[source_ref.id]
            destination = locked[destination_ref.id]

            now = datetime.now(timezone.utc)
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)

            monthly_count = self.transaction_repository.count_source_transfers(
                source.id, period_start, period_end
            )
            free_limit = (
                source.monthly_free_transfers_limit
                if source.monthly_free_transfers_limit is not None
                else DEFAULT_MONTHLY_FREE_TRANSFERS_LIMIT
            )

            fee_amount = calculate_fee(monthly_count, free_limit, source.balance)

            total_debit = amount + fee_amount
            if source.balance < total_debit:
                raise InsufficientBalance()

            self.account_repository.update_balance(source, source.balance - total_debit)
            self.account_repository.update_balance(destination, destination.balance + amount)

            transaction = Transaction(
                transaction_key=str(uuid4()),
                source_account_id=source.id,
                destination_account_id=destination.id,
                amount=amount,
                fee_amount=fee_amount,
                created_at=now,
            )
            self.transaction_repository.create(transaction)

            # This is the only commit in the normal transfer flow.
            self.session.commit()
            return TransactionDTO.obj_to_dict(transaction, is_fee_exempt=(fee_amount == 0))
        except Exception:
            self.session.rollback()
            raise
