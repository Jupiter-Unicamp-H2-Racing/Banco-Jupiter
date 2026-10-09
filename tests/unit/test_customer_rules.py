import json
from datetime import date
from pathlib import Path

from controllers.customer_controller import CustomerController, MINIMUM_AGE, MAXIMUM_AGE
from models.customer_status import CustomerStatus


def test_customer_age_boundaries_are_explicit():
    assert MINIMUM_AGE == 18
    assert MAXIMUM_AGE == 80
    assert CustomerController._age_in_years(date.today().replace(year=date.today().year - 18)) >= 18


def test_customer_statuses_match_database_seed_values():
    sql = Path("/database/database.sql").read_text(encoding="utf-8")
    expected = {"pending_kyc", "active", "blocked", "inactive"}
    assert set(CustomerStatus.ALLOWED) == expected
    for status in expected:
        assert f"('{status}')" in sql


def test_all_json_schemas_parse():
    for schema_path in Path("src/schemas").glob("*.json"):
        with schema_path.open(encoding="utf-8") as schema_file:
            assert isinstance(json.load(schema_file), dict)
