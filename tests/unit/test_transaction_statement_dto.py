from datetime import datetime, timezone
from types import SimpleNamespace

from dtos.transaction_dto import TransactionDTO


def test_statement_dto_derives_direction_and_never_exposes_internal_ids():
    timestamp = datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)
    debit = SimpleNamespace(
        transaction_key="debit-key", source_account_id=10, destination_account_id=20,
        amount=2500, fee_amount=100, created_at=timestamp, id=91,
    )
    credit = SimpleNamespace(
        transaction_key="credit-key", source_account_id=20, destination_account_id=10,
        amount=700, fee_amount=50, created_at=timestamp, id=92,
    )

    result = TransactionDTO.list_to_dict([(debit, "counterparty-debit"), (credit, "counterparty-credit")],
                                         account_id=10, page=1, limit=20, total_items=2)

    assert result["items"][0]["direction"] == "debit"
    assert result["items"][0]["fee_amount"] == 100
    assert result["items"][0]["counterparty_account_key"] == "counterparty-debit"
    assert result["items"][1]["direction"] == "credit"
    assert result["items"][1]["fee_amount"] == 0
    assert result["pagination"] == {"total_items": 2, "page": 1, "limit": 20}
    for item in result["items"]:
        assert not {"id", "source_account_id", "destination_account_id"}.intersection(item)
    assert not {"id", "source_account_id", "destination_account_id"}.intersection(result)
