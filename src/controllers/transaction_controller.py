from datetime import date, datetime, time, timedelta, timezone
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
    IdempotencyConflict
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

    def list(self, account_key: str, limit: int = 20, page: int = 1,
             start_date: str = None, end_date: str = None) -> dict:
        account = self._ensure_account_access(account_key)
        parsed_start = self._parse_statement_date(start_date) if start_date else None
        parsed_end = self._parse_statement_date(end_date) if end_date else None
        if parsed_start is not None and parsed_end is not None and parsed_start > parsed_end:
            raise InvalidDateRange(start_date, end_date)

        start_datetime = datetime.combine(parsed_start, time.min, tzinfo=timezone.utc) if parsed_start else None
        end_datetime = datetime.combine(parsed_end + timedelta(days=1), time.min,
                                        tzinfo=timezone.utc) if parsed_end else None
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
        destination_key = payload["destination_account_key"]

        try:
            # Valida a chave quando ela for informada.
            if idempotency_key is not None:
                if (
                    not isinstance(idempotency_key, str)
                    or not idempotency_key.strip()
                    or len(idempotency_key) > 255
                ):
                    raise InvalidParameter(
                        "Idempotency-Key must contain 1 to 255 characters "
                        "and cannot consist only of whitespace."
                    )

            # Localiza as contas envolvidas.
            source_ref = self.account_repository.get_by_key(
                source_account_key
            )
            if source_ref is None:
                raise AccountNotFound(source_account_key)

            destination_ref = self.account_repository.get_by_key(
                destination_key
            )
            if destination_ref is None:
                raise AccountNotFound(destination_key)

            if source_ref.id == destination_ref.id:
                raise InvalidTransfer(
                    "Transfers to the same account are not allowed."
                )

            # Bloqueia as contas sempre na mesma ordem.
            locked = {}

            for account_id in sorted(
                (source_ref.id, destination_ref.id)
            ):
                locked_account = (
                    self.account_repository.get_by_id_for_update(
                        account_id
                    )
                )

                if locked_account is None:
                    missing_key = (
                        source_account_key
                        if account_id == source_ref.id
                        else destination_key
                    )
                    raise AccountNotFound(missing_key)

                locked[account_id] = locked_account

            source = locked[source_ref.id]
            destination = locked[destination_ref.id]

            # Consulta a chave depois de obter os bloqueios.
            if idempotency_key is not None:
                existing = (
                    self.transaction_repository.get_by_idempotency_key(
                        source.id,
                        idempotency_key,
                    )
                )

                if existing is not None:
                    # A mesma chave deve representar a mesma operacao.
                    if (
                        existing.destination_account_id != destination.id
                        or existing.amount != amount
                    ):
                        raise IdempotencyConflict()

                    response = TransactionDTO.obj_to_dict(
                        existing,
                        is_fee_exempt=(existing.fee_amount == 0),
                    )

                    # Libera os bloqueios sem movimentar dinheiro novamente.
                    self.session.commit()
                    return response

            # Define o intervalo do mes atual em UTC.
            now = datetime.now(timezone.utc)
            period_start = now.replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

            if period_start.month == 12:
                period_end = period_start.replace(
                    year=period_start.year + 1,
                    month=1,
                )
            else:
                period_end = period_start.replace(
                    month=period_start.month + 1
                )

            monthly_count = (
                self.transaction_repository.count_source_transfers(
                    source.id,
                    period_start,
                    period_end,
                )
            )

            free_limit = (
                source.monthly_free_transfers_limit
                if source.monthly_free_transfers_limit is not None
                else DEFAULT_MONTHLY_FREE_TRANSFERS_LIMIT
            )

            fee_amount = calculate_fee(
                monthly_count,
                free_limit,
                source.balance,
            )

            total_debit = amount + fee_amount

            if source.balance < total_debit:
                raise InsufficientBalance()

            # Atualiza os saldos na mesma transacao do banco.
            self.account_repository.update_balance(
                source,
                source.balance - total_debit,
            )
            self.account_repository.update_balance(
                destination,
                destination.balance + amount,
            )

            # Registra a transferencia junto com a chave.
            transaction = Transaction(
                transaction_key=str(uuid4()),
                idempotency_key=idempotency_key,
                source_account_id=source.id,
                destination_account_id=destination.id,
                amount=amount,
                fee_amount=fee_amount,
                created_at=now,
            )

            self.transaction_repository.create(transaction)
            self.session.commit()

            return TransactionDTO.obj_to_dict(
                transaction,
                is_fee_exempt=(fee_amount == 0),
            )

        except Exception:
            self.session.rollback()
            raise