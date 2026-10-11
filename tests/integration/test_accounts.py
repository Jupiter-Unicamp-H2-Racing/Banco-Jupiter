"""Fluxos de conta: abertura vinculada a um cliente ativo e consulta."""
from uuid import uuid4

import pytest

from tests.utils.object_generator import ObjectGenerator
from tests.utils.request_generator import RequestGenerator

pytestmark = pytest.mark.integration


def test_create_account_links_to_the_customer_and_returns_only_the_key():
    customer_key = ObjectGenerator.create_active_customer()
    status, body = RequestGenerator.POST_account({"customer_key": customer_key})
    assert status == 201
    assert list(body) == ["account_key"]

    status, account = RequestGenerator.GET_account(body["account_key"])
    assert status == 200
    assert account == {"account_key": body["account_key"], "balance": 0,
                       "customer_key": customer_key, "tier": "STANDARD"}


def test_customer_can_have_several_accounts_and_initial_balance_is_kept():
    customer_key = ObjectGenerator.create_active_customer()
    first = ObjectGenerator.create_account(customer_key, 1500)
    second = ObjectGenerator.create_account(customer_key)
    assert first != second
    assert RequestGenerator.GET_account(first)[1]["balance"] == 1500
    assert RequestGenerator.GET_account(second)[1]["customer_key"] == customer_key


def test_create_account_requires_an_existing_customer():
    status, body = RequestGenerator.POST_account({"customer_key": str(uuid4())})
    assert (status, body["code"]) == (404, "QIT001001")


@pytest.mark.parametrize("final_status", ["blocked", "inactive"])
def test_create_account_requires_an_active_customer(final_status):
    pending = ObjectGenerator.create_customer()
    status, body = RequestGenerator.POST_account({"customer_key": pending})
    assert (status, body["code"]) == (422, "QIT001009")

    other = ObjectGenerator.create_customer()
    ObjectGenerator.update_customer(other, final_status)
    status, body = RequestGenerator.POST_account({"customer_key": other})
    assert (status, body["code"]) == (422, "QIT001009")


@pytest.mark.parametrize("payload", [
    {},
    {"customer_key": "not-a-uuid"},
    {"customer_key": "00000000-0000-4000-8000-000000000000", "unexpected": True},
    {"customer_key": "00000000-0000-4000-8000-000000000000", "initial_balance": -1},
    {"customer_key": "00000000-0000-4000-8000-000000000000", "initial_balance": "10"},
    {"customer_key": "00000000-0000-4000-8000-000000000000", "initial_balance": 1.5},
])
def test_create_account_rejects_invalid_payloads(payload):
    assert RequestGenerator.POST_account(payload)[0] == 400


def test_get_account_404_for_unknown_key_and_requires_token():
    status, body = RequestGenerator.GET_account(str(uuid4()))
    assert (status, body["code"]) == (404, "QIT002001")
    assert RequestGenerator.POST_account({}, headers={})[0] == 403


def test_initial_balance_bigint_limit_and_upper_bound():
    customer_key = ObjectGenerator.create_active_customer()
    status, _ = RequestGenerator.POST_account({"customer_key": customer_key, "initial_balance": 10**20})
    assert status == 400
    status, body = RequestGenerator.POST_account({"customer_key": customer_key, "initial_balance": 9223372036854775807})
    assert status == 201
    assert RequestGenerator.GET_account(body["account_key"])[1]["balance"] == 9223372036854775807


def test_account_key_lookup_accepts_uppercase_uuid():
    key = ObjectGenerator.create_account()
    status, body = RequestGenerator.GET_account(key.upper())
    assert status == 200
    assert body["account_key"] == key.lower()


def test_account_creation_accepts_uppercase_customer_uuid():
    customer_key = ObjectGenerator.create_active_customer()
    status, body = RequestGenerator.POST_account({"customer_key": customer_key.upper()})
    assert status == 201
    assert RequestGenerator.GET_account(body["account_key"])[1]["customer_key"] == customer_key.lower()
