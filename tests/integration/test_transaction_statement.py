from os import environ
from uuid import uuid4

from sqlalchemy import create_engine, text

from tests.utils.db_utils import DbUtils
from tests.utils.requisition import ClientRequisition


INTERNAL_TOKEN = environ.get("INTERNAL_TOKEN", "default_token")
HEADERS = {"INTERNAL-TOKEN": INTERNAL_TOKEN}


def _seed_statement():
    DbUtils.rollback()
    engine = create_engine(DbUtils.database_url())
    source_key, destination_key, third_key = str(uuid4()), str(uuid4()), str(uuid4())
    with engine.begin() as connection:
        source_id = connection.execute(
            text("INSERT INTO account (account_key, balance) VALUES (:key, 100000) RETURNING id"),
            {"key": source_key},
        ).scalar_one()
        destination_id = connection.execute(
            text("INSERT INTO account (account_key, balance) VALUES (:key, 100000) RETURNING id"),
            {"key": destination_key},
        ).scalar_one()
        third_id = connection.execute(
            text("INSERT INTO account (account_key, balance) VALUES (:key, 100000) RETURNING id"),
            {"key": third_key},
        ).scalar_one()
        for transaction_source, transaction_destination, amount, fee, created, key in [
            (source_id, destination_id, 1000, 100, "2026-01-01T10:00:00+00:00", str(uuid4())),
            (third_id, source_id, 2000, 80, "2026-01-02T10:00:00+00:00", str(uuid4())),
            (source_id, destination_id, 3000, 0, "2026-01-03T10:00:00+00:00", str(uuid4())),
        ]:
            connection.execute(text('''
                INSERT INTO "transaction"
                    (transaction_key, source_account_id, destination_account_id, amount, fee_amount, created_at)
                VALUES (:key, :source, :destination, :amount, :fee, :created)
            '''), {"key": key, "source": transaction_source, "destination": transaction_destination,
                  "amount": amount, "fee": fee, "created": created})
    engine.dispose()
    return source_key, destination_key, third_key


def _get(account_key, params=None):
    return ClientRequisition.send("GET", f"/accounts/{account_key}/transactions", headers=HEADERS,
                                  query_params=params)


def test_statement_includes_debits_credits_and_deterministic_pagination():
    source, destination, _ = _seed_statement()
    response = _get(source, {"limit": "2", "page": "1"})
    assert response.response_status == 200
    body = response.response_json
    assert len(body["items"]) == 2
    assert body["pagination"] == {"total_items": 3, "page": 1, "limit": 2}
    assert body["items"][0]["direction"] == "debit"
    assert body["items"][0]["created_at"] > body["items"][1]["created_at"]
    assert body["items"][0]["counterparty_account_key"] == destination
    assert body["items"][0]["fee_amount"] == 0
    assert body["items"][1]["direction"] == "credit"
    assert body["items"][1]["fee_amount"] == 0
    assert not {"id", "source_account_id", "destination_account_id"}.intersection(body)
    assert all(not {"id", "source_account_id", "destination_account_id"}.intersection(item)
               for item in body["items"])

    page_two = _get(source, {"limit": "2", "page": "2"})
    assert page_two.response_status == 200
    assert len(page_two.response_json["items"]) == 1
    assert page_two.response_json["pagination"]["total_items"] == 3
    assert page_two.response_json["items"][0]["fee_amount"] == 100


def test_statement_empty_and_inclusive_date_filter():
    source, _, third = _seed_statement()
    empty = _get(third, {"start_date": "2026-02-01", "end_date": "2026-02-28"})
    assert empty.response_status == 200
    assert empty.response_json["items"] == []
    assert empty.response_json["pagination"]["total_items"] == 0

    filtered = _get(source, {"start_date": "2026-01-02", "end_date": "2026-01-02"})
    assert filtered.response_status == 200
    assert len(filtered.response_json["items"]) == 1
    assert filtered.response_json["items"][0]["direction"] == "credit"


def test_statement_validates_account_query_and_dates():
    source, _, _ = _seed_statement()
    missing = _get(str(uuid4()))
    assert missing.response_status == 404
    assert missing.response_json["code"] == "QIT002001"

    unknown = _get(source, {"limti": "20"})
    assert unknown.response_status == 400
    for params in ({"limit": "0"}, {"limit": "101"}, {"page": "0"}):
        assert _get(source, params).response_status == 400

    invalid_date = _get(source, {"start_date": "2025-02-30"})
    assert invalid_date.response_status == 422
    assert invalid_date.response_json["code"] == "QIT002004"
    invalid_range = _get(source, {"start_date": "2026-02-02", "end_date": "2026-02-01"})
    assert invalid_range.response_status == 422
    assert invalid_range.response_json["code"] == "QIT002005"
