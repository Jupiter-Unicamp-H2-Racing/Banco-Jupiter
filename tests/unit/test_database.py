import pytest

import database


class SessionStub:
    def __init__(self):
        self.rollbacks = 0
        self.closed = False

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def test_get_db_closes_session_without_committing(monkeypatch):
    session = SessionStub()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)
    dependency = database.get_db()

    assert next(dependency) is session
    with pytest.raises(StopIteration):
        next(dependency)

    assert session.rollbacks == 0
    assert session.closed is True


def test_get_db_rolls_back_and_closes_on_exception(monkeypatch):
    session = SessionStub()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)
    dependency = database.get_db()
    assert next(dependency) is session

    with pytest.raises(RuntimeError, match="failure"):
        dependency.throw(RuntimeError("failure"))

    assert session.rollbacks == 1
    assert session.closed is True


def test_get_db_fails_clearly_without_database_url(monkeypatch):
    monkeypatch.setattr(database, "SessionLocal", None)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        next(database.get_db())


def test_statement_and_customer_schemas_share_limit_contract():
    import json
    from pathlib import Path
    from constants import MAX_LIMIT

    root = Path(__file__).resolve().parents[2]
    for filename in ("get_customer.json", "get_transactions.json"):
        schema = json.loads((root / "src" / "schemas" / filename).read_text())
        pattern = schema["properties"]["limit"]["pattern"]
        assert pattern == rf"^({MAX_LIMIT}|[1-9][0-9]?)$"
