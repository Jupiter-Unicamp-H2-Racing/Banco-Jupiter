from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy.orm import Session
from uuid import uuid4

from controllers.base_controller import BaseController
from dtos.transaction_dto import TransactionDTO
from errors import InvalidParameter
from errors.custom_errors import (
    AccountNotFound,
    InsufficientBalance,
    InvalidDateRange,
    InvalidStatementDate,
    InvalidTransfer,
    IdempotencyConflict,
    BalanceOverflow,
    SourceCustomerNotActive,
    DestinationCustomerNotActive,
)
from models.transaction import Transaction
from repositories.account_repository import AccountRepository
from repositories.transaction_repository import TransactionRepository

from constants import (BUSINESS_TIMEZONE, DEFAULT_LIMIT, DEFAULT_PAGE, MAX_BALANCE, MAX_LIMIT,
                       FEE_REVENUE_ACCOUNT_KEY)
from utils.transaction_fee import DEFAULT_MONTHLY_FREE_TRANSFERS_LIMIT, calculate_fee
from utils.transaction_policy import monthly_window, validate_idempotency_key


class TransactionController(BaseController):
    def __init__(self, session: Session) -> None:
        super().__init__(session, __name__)
        self.account_repository = AccountRepository(session)
        self.transaction_repository = TransactionRepository(session)

    def list_from_query(self, account_key: str, params) -> dict:
        limit = int(params.get("limit", DEFAULT_LIMIT))
        page = int(params.get("page", DEFAULT_PAGE))
        if limit < 1 or limit > MAX_LIMIT or page < 1:
            raise InvalidParameter("limit or page is outside the allowed range")
        return self.list(
            account_key,
            limit=limit,
            page=page,
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
        )

    def list(self, account_key: str, limit: int = 20, page: int = 1,
             start_date: str = None, end_date: str = None) -> dict:
        account_key = account_key.lower()
        account = self._ensure_account_access(account_key)
        parsed_start = self._parse_statement_date(start_date) if start_date else None
        parsed_end = self._parse_statement_date(end_date) if end_date else None
        if parsed_start is not None and parsed_end is not None and parsed_start > parsed_end:
            raise InvalidDateRange(start_date, end_date)

        start_datetime = datetime.combine(parsed_start, time.min, tzinfo=timezone.utc) if parsed_start else None
        end_datetime = (datetime.combine(parsed_end + timedelta(days=1), time.min, tzinfo=timezone.utc)
                        if parsed_end is not None and parsed_end < date.max else None)
        rows = self.transaction_repository.list_by_account(
            account.id, limit, (page - 1) * limit, start_datetime, end_datetime
        )
        total_items = self.transaction_repository.count_by_account(account.id, start_datetime, end_datetime)
        return TransactionDTO.list_to_dict(rows, account.id, page, limit, total_items)

    def _ensure_account_access(self, account_key: str):
        # Hoje não há identidade de cliente autenticado; no futuro, verificar
        # autorização aqui e usar o mesmo 404 para contas inexistentes/terceiras.
        account = self.account_repository.get_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        return account

    @staticmethod
    def _parse_statement_date(value: str) -> date:
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise InvalidStatementDate(value) from exc

    def create(
        self,
        source_account_key: str,
        payload: dict,
        idempotency_key: str | None = None,
    ) -> dict:
        amount = payload["amount"]
        source_account_key = source_account_key.lower()
        destination_key = payload["destination_account_key"].lower()
        try:
            validate_idempotency_key(idempotency_key)
            source, destination, fee_account = self._lock_transfer_accounts(
                source_account_key, destination_key
            )
            self._validate_transfer_customers(source, destination)
            replay = self._get_idempotent_replay(source, destination, amount, idempotency_key)
            if replay is not None:
                self.session.commit()
                return replay
            now = datetime.now(timezone.utc)
            fee_amount = self._calculate_transfer_fee(source, now)
            self._apply_transfer_balances(source, destination, fee_account, amount, fee_amount)
            transaction = self._build_transfer_transaction(
                source, destination, fee_account, amount, fee_amount, idempotency_key, now
            )
            self.transaction_repository.create(transaction)
            self.session.commit()
            return TransactionDTO.obj_to_dict(transaction, is_fee_exempt=(fee_amount == 0))
        except Exception:
            self.session.rollback()
            raise

    def _lock_transfer_accounts(self, source_key: str, destination_key: str):
        source_ref = self.account_repository.get_by_key(source_key)
        if source_ref is None:
            raise AccountNotFound(source_key)
        destination_ref = self.account_repository.get_by_key(destination_key)
        if destination_ref is None:
            raise AccountNotFound(destination_key)
        if source_ref.id == destination_ref.id:
            raise InvalidTransfer("Transfers to the same account are not allowed.")
        fee_ref = self.account_repository.get_by_key(FEE_REVENUE_ACCOUNT_KEY)
        if fee_ref is None:
            raise RuntimeError("Fee revenue account is not seeded")
        # A conta de receita é interna: não pode participar de transferências
        # comuns. A comparação por ID também protege o caso em que a chave
        # pública foi normalizada ou o objeto já veio carregado pelo repository.
        fee_key = FEE_REVENUE_ACCOUNT_KEY
        source_key_is_fee = getattr(source_ref, "account_key", "").strip() == fee_key
        destination_key_is_fee = getattr(destination_ref, "account_key", "").strip() == fee_key
        if (source_key_is_fee or destination_key_is_fee or
                source_ref.id == fee_ref.id or destination_ref.id == fee_ref.id):
            raise InvalidTransfer("The fee revenue account cannot be used in ordinary transfers.")
        locked = {}
        for account_id in sorted({source_ref.id, destination_ref.id, fee_ref.id}):
            account = self.account_repository.get_by_id_for_update(account_id)
            if account is None:
                raise AccountNotFound(source_key if account_id == source_ref.id else destination_key)
            locked[account_id] = account
        return locked[source_ref.id], locked[destination_ref.id], locked[fee_ref.id]

    @staticmethod
    def _validate_transfer_customers(source, destination) -> None:
        source_customer = source.customer
        source_status = source_customer.status.enumerator
        if source_status != "active":
            raise SourceCustomerNotActive(source_customer.customer_key, source_status)
        destination_customer = destination.customer
        destination_status = destination_customer.status.enumerator
        if destination_status != "active":
            raise DestinationCustomerNotActive(destination_customer.customer_key, destination_status)

    def _get_idempotent_replay(self, source, destination, amount, idempotency_key):
        if idempotency_key is None:
            return None
        existing = self.transaction_repository.get_by_idempotency_key(source.id, idempotency_key)
        if existing is None:
            return None
        if existing.destination_account_id != destination.id or existing.amount != amount:
            raise IdempotencyConflict()
        return TransactionDTO.obj_to_dict(existing, is_fee_exempt=(existing.fee_amount == 0))

    def _calculate_transfer_fee(self, source, now: datetime) -> int:
        period_start, period_end = monthly_window(now, BUSINESS_TIMEZONE)
        monthly_count = self.transaction_repository.count_source_transfers(
            source.id, period_start, period_end
        )
        free_limit = (
            source.monthly_free_transfers_limit
            if source.monthly_free_transfers_limit is not None
            else DEFAULT_MONTHLY_FREE_TRANSFERS_LIMIT
        )
        return calculate_fee(monthly_count, free_limit, source.balance)

    def _apply_transfer_balances(self, source, destination, fee_account, amount, fee_amount) -> None:
        total_debit = amount + fee_amount
        if source.balance < total_debit:
            raise InsufficientBalance()
        # Calcule o crédito total por conta antes de alterar qualquer saldo.
        # A conta de receita é proibida como destino comum acima, mas a
        # agregação também protege contra referências repetidas no futuro.
        credits = {destination.id: amount}
        if fee_amount > 0:
            credits[fee_account.id] = credits.get(fee_account.id, 0) + fee_amount
        accounts = {destination.id: destination, fee_account.id: fee_account}
        for account_id, credit in credits.items():
            if accounts[account_id].balance + credit > MAX_BALANCE:
                raise BalanceOverflow()
        self.account_repository.update_balance(source, source.balance - total_debit)
        self.account_repository.update_balance(destination, destination.balance + amount)
        if fee_amount > 0:
            self.account_repository.update_balance(fee_account, fee_account.balance + fee_amount)

    @staticmethod
    def _build_transfer_transaction(
        source, destination, fee_account, amount, fee_amount, idempotency_key, now
    ) -> Transaction:
        return Transaction(
            transaction_key=str(uuid4()),
            idempotency_key=idempotency_key,
            source_account_id=source.id,
            destination_account_id=destination.id,
            amount=amount,
            fee_amount=fee_amount,
            fee_account_id=fee_account.id if fee_amount > 0 else None,
            kind="transfer",
            created_at=now,
        )
