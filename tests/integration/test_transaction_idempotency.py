"""Idempotencia: repeticao, conflito, tarifa e concorrencia."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest

from tests.utils.object_generator import ObjectGenerator
from tests.utils.request_generator import INTERNAL_TOKEN, RequestGenerator


pytestmark = pytest.mark.integration


def _transfer(source, destination, amount, key):
    return RequestGenerator.POST_transaction(
        source,
        {
            "destination_account_key": destination,
            "amount": amount,
        },
        headers={
            "INTERNAL-TOKEN": INTERNAL_TOKEN,
            "Idempotency-Key": key,
        },
    )


def _balance(account_key):
    status, body = RequestGenerator.GET_account(account_key)
    assert status == 200, body
    return body["balance"]


def _total_transactions(account_key):
    status, body = RequestGenerator.GET_transactions(account_key)
    assert status == 200, body
    return body["pagination"]["total_items"]


def test_retry_returns_original_receipt_without_charging_again():
    source = ObjectGenerator.create_account(balance=1_000)
    destination = ObjectGenerator.create_account()

    # Consome as cinco transferencias gratuitas.
    for _ in range(5):
        status, body = _transfer(
            source, destination, 1, str(uuid4())
        )
        assert status == 201, body
        assert body["fee_amount"] == 0

    key = str(uuid4())

    status, original = _transfer(source, destination, 900, key)
    assert status == 201, original
    assert original["fee_amount"] == 50
    assert original["is_fee_exempt"] is False

    # O saldo restante nao permite outra transferencia de 900.
    # Mesmo assim, a repeticao deve devolver o resultado original.
    status, repeated = _transfer(source, destination, 900, key)
    assert status == 201, repeated
    assert repeated == original

    assert _balance(source) == 45
    assert _balance(destination) == 905
    assert _total_transactions(source) == 6
    assert _total_transactions(destination) == 6


@pytest.mark.parametrize("changed_field", ["amount", "destination"])
def test_reusing_key_with_different_data_returns_conflict(changed_field):
    source = ObjectGenerator.create_account(balance=1_000)
    destination = ObjectGenerator.create_account()
    other_destination = ObjectGenerator.create_account()
    key = str(uuid4())

    status, body = _transfer(source, destination, 100, key)
    assert status == 201, body

    amount = 200 if changed_field == "amount" else 100
    target = (
        other_destination
        if changed_field == "destination"
        else destination
    )

    status, body = _transfer(source, target, amount, key)

    assert status == 409, body
    assert body["code"] == "QIT002006"
    assert _balance(source) == 900
    assert _balance(destination) == 100
    assert _balance(other_destination) == 0
    assert _total_transactions(source) == 1
    assert _total_transactions(destination) == 1
    assert _total_transactions(other_destination) == 0


def test_concurrent_requests_with_same_key_execute_once():
    source = ObjectGenerator.create_account(balance=1_000)
    destination = ObjectGenerator.create_account()
    key = str(uuid4())
    barrier = Barrier(8)

    def send_request(_):
        # Aproxima o inicio das oito chamadas.
        barrier.wait(timeout=10)
        return _transfer(source, destination, 300, key)

    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(send_request, range(8)))

    for status, body in responses:
        assert status == 201, body

    original = responses[0][1]
    assert all(body == original for _, body in responses)
    assert original["fee_amount"] == 0

    assert _balance(source) == 700
    assert _balance(destination) == 300
    assert _total_transactions(source) == 1
    assert _total_transactions(destination) == 1


def test_distinct_keys_execute_and_retries_do_not_consume_allowance():
    source = ObjectGenerator.create_account(balance=1_000)
    destination = ObjectGenerator.create_account()
    transaction_keys = set()

    for _ in range(5):
        key = str(uuid4())

        status, original = _transfer(source, destination, 10, key)
        assert status == 201, original
        assert original["fee_amount"] == 0
        transaction_keys.add(original["transaction_key"])

        status, repeated = _transfer(source, destination, 10, key)
        assert status == 201, repeated
        assert repeated == original

    # Cinco chaves diferentes devem gerar cinco transferencias.
    assert len(transaction_keys) == 5
    assert _total_transactions(source) == 5

    # A sexta transferencia real deve cobrar a tarifa.
    status, body = _transfer(
        source, destination, 10, str(uuid4())
    )
    assert status == 201, body
    assert body["fee_amount"] == 50

    assert _balance(source) == 890
    assert _balance(destination) == 60
    assert _total_transactions(source) == 6
    assert _total_transactions(destination) == 6


def test_same_key_can_be_used_by_different_source_accounts():
    source_a = ObjectGenerator.create_account(balance=1_000)
    source_b = ObjectGenerator.create_account(balance=1_000)
    destination = ObjectGenerator.create_account()
    key = str(uuid4())

    status_a, body_a = _transfer(source_a, destination, 100, key)
    status_b, body_b = _transfer(source_b, destination, 100, key)

    assert status_a == 201, body_a
    assert status_b == 201, body_b
    assert body_a["transaction_key"] != body_b["transaction_key"]

    assert _balance(source_a) == 900
    assert _balance(source_b) == 900
    assert _balance(destination) == 200
    assert _total_transactions(source_a) == 1
    assert _total_transactions(source_b) == 1
    assert _total_transactions(destination) == 2


@pytest.mark.parametrize("key", ["", "x" * 256], ids=["empty", "too_long"])
def test_invalid_idempotency_key_does_not_move_money(key):
    source = ObjectGenerator.create_account(balance=1_000)
    destination = ObjectGenerator.create_account()

    status, body = _transfer(source, destination, 100, key)

    assert status == 400, body
    assert body["code"] == "QIT000010"
    assert _balance(source) == 1_000
    assert _balance(destination) == 0
    assert _total_transactions(source) == 0
    assert _total_transactions(destination) == 0