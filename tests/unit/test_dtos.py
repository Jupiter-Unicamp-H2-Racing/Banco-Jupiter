from datetime import date, datetime, timezone
from types import SimpleNamespace

from dtos.account_dto import AccountDTO
from dtos.customer_dto import CustomerDTO


def _customer():
    event = SimpleNamespace(status=SimpleNamespace(enumerator="pending_kyc"),
                            event_datetime=datetime(2026, 1, 1, tzinfo=timezone.utc))
    return SimpleNamespace(id=7, customer_key="abc ", name="Ana", email="a@x.com",
                           document_number="529.982.247-25", birthdate=date(1990, 1, 1),
                           status=SimpleNamespace(enumerator="active"), status_events=[event])


def test_customer_dto_hides_internal_fields_and_strips_char_padding():
    result = CustomerDTO.obj_to_dict(_customer())
    assert result["customer_key"] == "abc"
    assert result["birthdate"] == "1990-01-01"
    assert result["status_events"] == [{"status": "pending_kyc", "event_datetime": "2026-01-01T00:00:00+00:00"}]
    assert "id" not in result and "status_id" not in result
    assert CustomerDTO.only_obj_key(_customer()) == {"customer_key": "abc"}
    assert "status_events" not in CustomerDTO.list_obj_to_list_dict([_customer()])[0]


def test_account_dto_exposes_balance_and_customer_key_but_not_ids():
    account = SimpleNamespace(id=3, customer_id=7, account_key="acc-key ", balance=1234, tier_code="STANDARD",
                              customer=SimpleNamespace(customer_key="cus-key "))
    assert AccountDTO.only_obj_key(account) == {"account_key": "acc-key"}
    assert AccountDTO.obj_to_dict(account) == {"account_key": "acc-key", "balance": 1234,
                                               "customer_key": "cus-key", "tier": "STANDARD"}
