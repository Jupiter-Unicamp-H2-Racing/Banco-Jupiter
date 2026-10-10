"""Fluxo de transferência: saldo, tarifa, validações, token e concorrência."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from tests.utils.object_generator import ObjectGenerator
from tests.utils.request_generator import RequestGenerator

pytestmark = pytest.mark.integration

FEE = 50
FREE_TRANSFERS = 5
FEE_EXEMPTION_BALANCE = 100_000


def _transfer(source, destination, amount):
    return RequestGenerator.POST_transaction(
        source, {"destination_account_key": destination, "amount": amount})


def _balance(account_key):
    return RequestGenerator.GET_account(account_key)[1]["balance"]


def test_transfer_moves_money_and_returns_receipt():
    source = ObjectGenerator.create_account(balance=10_000)
    destination = ObjectGenerator.create_account()
    status, body = _transfer(source, destination, 2_500)
    assert status == 201
    assert set(body) == {"transaction_key", "amount", "fee_amount", "is_fee_exempt"}
    assert (body["amount"], body["fee_amount"], body["is_fee_exempt"]) == (2_500, 0, True)
    assert (_balance(source), _balance(destination)) == (7_500, 2_500)


def test_fee_starts_after_the_free_allowance_and_is_paid_by_the_source_only():
    source = ObjectGenerator.create_account(balance=10_000)
    destination = ObjectGenerator.create_account()
    for _ in range(FREE_TRANSFERS):
        assert _transfer(source, destination, 100)[1]["fee_amount"] == 0
    status, body = _transfer(source, destination, 100)
    assert status == 201
    assert (body["fee_amount"], body["is_fee_exempt"]) == (FEE, False)
    assert _balance(source) == 10_000 - 6 * 100 - FEE
    assert _balance(destination) == 6 * 100


def test_high_balance_source_never_pays_fee():
    source = ObjectGenerator.create_account(balance=FEE_EXEMPTION_BALANCE + 10_000)
    destination = ObjectGenerator.create_account()
    for _ in range(FREE_TRANSFERS + 2):
        assert _transfer(source, destination, 1)[1]["fee_amount"] == 0


def test_insufficient_balance_is_rejected_and_nothing_changes():
    source = ObjectGenerator.create_account(balance=500)
    destination = ObjectGenerator.create_account()
    status, body = _transfer(source, destination, 501)
    assert (status, body["code"]) == (422, "QIT002002")
    assert (_balance(source), _balance(destination)) == (500, 0)
    assert RequestGenerator.GET_transactions(source)[1]["pagination"]["total_items"] == 0


def test_amount_that_fits_but_not_with_the_fee_is_rejected():
    source = ObjectGenerator.create_account(balance=1_000)
    destination = ObjectGenerator.create_account()
    for _ in range(FREE_TRANSFERS):
        assert _transfer(source, destination, 1)[0] == 201
    remaining = _balance(source)
    status, body = _transfer(source, destination, remaining)
    assert (status, body["code"]) == (422, "QIT002002")
    assert _balance(source) == remaining
    assert _transfer(source, destination, remaining - FEE)[0] == 201
    assert _balance(source) == 0


def test_transfer_to_the_same_account_and_unknown_accounts_are_rejected():
    account = ObjectGenerator.create_account(balance=1_000)
    other = ObjectGenerator.create_account()
    status, body = _transfer(account, account, 10)
    assert (status, body["code"]) == (422, "QIT002003")
    status, body = _transfer(str(uuid4()), other, 10)
    assert (status, body["code"]) == (404, "QIT002001")
    status, body = _transfer(account, str(uuid4()), 10)
    assert (status, body["code"]) == (404, "QIT002001")
    assert _balance(account) == 1_000


@pytest.mark.parametrize("payload", [
    {"destination_account_key": "not-a-uuid", "amount": 10},
    {"destination_account_key": "00000000-0000-4000-8000-000000000001", "amount": 0},
    {"destination_account_key": "00000000-0000-4000-8000-000000000001", "amount": -5},
    {"destination_account_key": "00000000-0000-4000-8000-000000000001", "amount": "10"},
    {"destination_account_key": "00000000-0000-4000-8000-000000000001", "amount": 1.5},
    {"destination_account_key": "00000000-0000-4000-8000-000000000001", "amount": 10, "extra": 1},
    {"amount": 10},
    {"destination_account_key": "00000000-0000-4000-8000-000000000001"},
])
def test_invalid_payloads_are_rejected_with_400(payload):
    status, _ = RequestGenerator.POST_transaction("00000000-0000-4000-8000-000000000000", payload)
    assert status == 400


def test_missing_or_wrong_internal_token_is_forbidden():
    payload = {"destination_account_key": "00000000-0000-4000-8000-000000000001", "amount": 100}
    source = "00000000-0000-4000-8000-000000000000"
    assert RequestGenerator.POST_transaction(source, payload, headers={})[0] == 403
    assert RequestGenerator.POST_transaction(source, payload, headers={"INTERNAL-TOKEN": "wrong"})[0] == 403


def test_transfers_appear_in_both_statements_with_matching_fee():
    source = ObjectGenerator.create_account(balance=5_000)
    destination = ObjectGenerator.create_account()
    for _ in range(FREE_TRANSFERS + 1):
        _transfer(source, destination, 100)
    _, source_statement = RequestGenerator.GET_transactions(source)
    _, destination_statement = RequestGenerator.GET_transactions(destination)
    assert source_statement["pagination"]["total_items"] == 6
    assert {i["direction"] for i in source_statement["items"]} == {"debit"}
    assert source_statement["items"][0]["fee_amount"] == FEE
    assert {i["direction"] for i in destination_statement["items"]} == {"credit"}
    assert all(i["fee_amount"] == 0 for i in destination_statement["items"])


def test_money_is_conserved_under_concurrent_opposite_transfers():
    a = ObjectGenerator.create_account(balance=FEE_EXEMPTION_BALANCE * 2)
    b = ObjectGenerator.create_account(balance=FEE_EXEMPTION_BALANCE * 2)

    def run(args):
        return _transfer(*args)[0]

    jobs = [(a, b, 10), (b, a, 7)] * 15
    with ThreadPoolExecutor(max_workers=10) as pool:
        statuses = list(pool.map(run, jobs))
    assert set(statuses) == {201}
    assert _balance(a) + _balance(b) == FEE_EXEMPTION_BALANCE * 4
    assert _balance(a) == FEE_EXEMPTION_BALANCE * 2 - 15 * 10 + 15 * 7


def test_concurrent_transfers_cannot_overdraw_the_source():
    source = ObjectGenerator.create_account(balance=1_000)
    destination = ObjectGenerator.create_account()
    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(lambda _: _transfer(source, destination, 300)[0], range(8)))
    assert statuses.count(201) == 3
    assert statuses.count(422) == 5
    assert _balance(source) == 100
    assert _balance(destination) == 900
