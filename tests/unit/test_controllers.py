"""Regras de negócio dos controllers, com repositórios falsos (sem banco)."""
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from controllers.account_controller import AccountController
from controllers.customer_controller import CustomerController
from controllers.transaction_controller import TransactionController
from errors.custom_errors import (AccountNotFound, CustomerNotActive, CustomerFinalStatus, DuplicatedDocumentNumber,
                                  DuplicatedEmail, InsufficientBalance, InvalidDateRange, InvalidDocumentNumber,
                                  InvalidStatementDate, InvalidTransfer, NotFoundCustomer, OverAgeCustomer,
                                  UnderageCustomer)
from errors import InvalidParameter


def _birth(years):
    today = date.today()
    return today.replace(year=today.year - years, day=1).isoformat()


VALID = {"name": "Ana", "email": "a@x.com", "document_number": "529.982.247-25", "birthdate": "1990-01-01"}


class FakeCustomerRepo:
    def __init__(self, existing=None, by_doc=None, by_email=None):
        self.existing, self.by_doc, self.by_email = existing, by_doc, by_email
        self.created = None
        self.new_status = None

    def get_by_document_number(self, _): return self.by_doc
    def get_by_email(self, _): return self.by_email
    def get_by_key(self, _): return self.existing

    def create(self, data):
        self.created = SimpleNamespace(**{**data, "birthdate": date.fromisoformat(data["birthdate"])}, customer_key="k",
                                       status=SimpleNamespace(enumerator="pending_kyc"), status_events=[])
        return self.created

    def update_status(self, customer, new_status): self.new_status = new_status


def _customer_controller(repo):
    controller = CustomerController()
    controller.customer_repository = repo
    return controller


def test_customer_create_commits_once_after_all_checks(fake_session):
    repo = FakeCustomerRepo()
    assert _customer_controller(repo).create(dict(VALID)) == {"customer_key": "k"}
    assert fake_session.commits == 1


@pytest.mark.parametrize("override,error", [
    ({"document_number": "111.222.333-44"}, InvalidDocumentNumber),
    ({"birthdate": _birth(17)}, UnderageCustomer),
    ({"birthdate": _birth(81)}, OverAgeCustomer),
])
def test_customer_create_rejections_never_commit(fake_session, override, error):
    repo = FakeCustomerRepo()
    with pytest.raises(error):
        _customer_controller(repo).create({**VALID, **override})
    assert fake_session.commits == 0 and repo.created is None


def test_customer_create_rejects_duplicates(fake_session):
    with pytest.raises(DuplicatedDocumentNumber):
        _customer_controller(FakeCustomerRepo(by_doc=object())).create(dict(VALID))
    with pytest.raises(DuplicatedEmail):
        _customer_controller(FakeCustomerRepo(by_email=object())).create(dict(VALID))
    assert fake_session.commits == 0


def test_customer_update_status_rules(fake_session):
    pending = SimpleNamespace(status=SimpleNamespace(enumerator="pending_kyc"), customer_key="k", name="n",
                              email="e", document_number="d", birthdate=date(1990, 1, 1), status_events=[])
    repo = FakeCustomerRepo(existing=pending)
    _customer_controller(repo).update_status("k", "active")
    assert repo.new_status == "active" and fake_session.commits == 1

    with pytest.raises(InvalidParameter):
        _customer_controller(repo).update_status("k", "pending_kyc")
    with pytest.raises(NotFoundCustomer):
        _customer_controller(FakeCustomerRepo()).update_status("k", "active")
    final = SimpleNamespace(status=SimpleNamespace(enumerator="active"))
    with pytest.raises(CustomerFinalStatus):
        _customer_controller(FakeCustomerRepo(existing=final)).update_status("k", "blocked")


def test_customer_list_birthdate_range_is_validated(fake_session):
    with pytest.raises(InvalidParameter):
        _customer_controller(FakeCustomerRepo()).get_list(
            10, 0, {"birthdate_from": "2000-01-01", "birthdate_to": "1990-01-01"})


class FakeAccountRepo:
    def __init__(self, accounts=None):
        self.accounts = accounts or {}
        self.created = None

    def get_by_key(self, key): return self.accounts.get(key)
    def create(self, customer_id, balance, key):
        self.created = (customer_id, balance, key)
        return SimpleNamespace(account_key=key)

    def get_by_id_for_update(self, account_id):
        return next((a for a in self.accounts.values() if a.id == account_id), None)

    def update_balance(self, account, new_balance): account.balance = new_balance


def _account_controller(customer, accounts=None):
    controller = AccountController()
    controller.customer_repository = SimpleNamespace(get_by_key=lambda _: customer)
    controller.account_repository = FakeAccountRepo(accounts)
    return controller


def test_account_create_requires_existing_active_customer(fake_session):
    with pytest.raises(NotFoundCustomer):
        _account_controller(None).create({"customer_key": "k"})
    pending = SimpleNamespace(id=1, customer_key="k", status=SimpleNamespace(enumerator="pending_kyc"))
    with pytest.raises(CustomerNotActive):
        _account_controller(pending).create({"customer_key": "k"})
    assert fake_session.commits == 0

    active = SimpleNamespace(id=1, customer_key="k", status=SimpleNamespace(enumerator="active"))
    controller = _account_controller(active)
    result = controller.create({"customer_key": "k", "initial_balance": 500})
    assert controller.account_repository.created[:2] == (1, 500)
    assert result == {"account_key": controller.account_repository.created[2]}
    assert fake_session.commits == 1


def test_account_get_unknown_raises(fake_session):
    with pytest.raises(AccountNotFound):
        _account_controller(None).get_by_key("nope")


class FakeTransactionRepo:
    def __init__(self, monthly_count=0):
        self.monthly_count = monthly_count
        self.created = []

    def count_source_transfers(self, *_): return self.monthly_count
    def create(self, transaction):
        self.created.append(transaction)
        return transaction


def _transaction_controller(source, destination, monthly_count=0):
    controller = TransactionController()
    controller.account_repository = FakeAccountRepo({"src": source, "dst": destination})
    controller.transaction_repository = FakeTransactionRepo(monthly_count)
    return controller


def _account(id_, balance, limit=5):
    return SimpleNamespace(id=id_, balance=balance, monthly_free_transfers_limit=limit)


def test_transfer_debits_amount_plus_fee_and_credits_only_the_amount(fake_session):
    source, destination = _account(1, 10_000), _account(2, 0)
    controller = _transaction_controller(source, destination, monthly_count=5)
    result = controller.create("src", {"destination_account_key": "dst", "amount": 1_000})
    assert (source.balance, destination.balance) == (10_000 - 1_000 - 50, 1_000)
    assert (result["fee_amount"], result["is_fee_exempt"]) == (50, False)
    assert fake_session.commits == 1 and fake_session.rollbacks == 0


def test_transfer_inside_free_allowance_has_no_fee(fake_session):
    source, destination = _account(1, 10_000), _account(2, 0)
    result = _transaction_controller(source, destination, monthly_count=4).create(
        "src", {"destination_account_key": "dst", "amount": 1_000})
    assert result["fee_amount"] == 0 and source.balance == 9_000


def test_transfer_failures_roll_back_and_leave_balances_untouched(fake_session):
    source, destination = _account(1, 100), _account(2, 0)
    with pytest.raises(InsufficientBalance):
        _transaction_controller(source, destination).create("src", {"destination_account_key": "dst", "amount": 101})
    with pytest.raises(InvalidTransfer):
        _transaction_controller(source, source).create("src", {"destination_account_key": "dst", "amount": 1})
    with pytest.raises(AccountNotFound):
        _transaction_controller(source, None).create("src", {"destination_account_key": "dst", "amount": 1})
    with pytest.raises(AccountNotFound):
        _transaction_controller(None, destination).create("src", {"destination_account_key": "dst", "amount": 1})
    assert (source.balance, destination.balance) == (100, 0)
    assert fake_session.commits == 0 and fake_session.rollbacks == 4


def test_statement_date_validation(fake_session):
    controller = TransactionController()
    controller.account_repository = FakeAccountRepo({"a": _account(1, 0)})
    with pytest.raises(InvalidStatementDate):
        controller.list("a", start_date="2025-02-30")
    with pytest.raises(InvalidDateRange):
        controller.list("a", start_date="2026-02-02", end_date="2026-02-01")
    with pytest.raises(AccountNotFound):
        controller.list("missing")
