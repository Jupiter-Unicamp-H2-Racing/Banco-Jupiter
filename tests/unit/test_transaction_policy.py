from datetime import datetime, timezone

import pytest

from constants import MAX_BALANCE
from utils.transaction_policy import monthly_window, validate_idempotency_key
from errors import InvalidParameter


@pytest.mark.parametrize("instant", [
    datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc),
    datetime(2026, 10, 1, 2, 59, tzinfo=timezone.utc),
])
def test_month_window_uses_sao_paulo_business_month(instant):
    start, end = monthly_window(instant, "America/Sao_Paulo")
    assert start == datetime(2026, 9, 1, 3, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 10, 1, 3, 0, tzinfo=timezone.utc)


def test_month_window_changes_at_local_month_boundary():
    start, end = monthly_window(
        datetime(2026, 10, 1, 3, 0, tzinfo=timezone.utc),
        "America/Sao_Paulo",
    )
    assert start == datetime(2026, 10, 1, 3, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 11, 1, 3, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("value", ["", "   ", "x" * 256])
def test_invalid_idempotency_key_is_rejected(value):
    with pytest.raises(InvalidParameter):
        validate_idempotency_key(value)


def test_transaction_schema_bigint_limit_matches_constant():
    import json
    from pathlib import Path

    schema_path = Path(__file__).resolve().parents[2] / "src" / "schemas" / "post_transaction.json"
    schema = json.loads(schema_path.read_text())
    assert schema["properties"]["amount"]["maximum"] == MAX_BALANCE
