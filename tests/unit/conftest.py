from types import SimpleNamespace

import pytest

from controllers import base_controller


class FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@pytest.fixture
def fake_session(monkeypatch):
    """Troca o contexto de banco por um falso: controllers rodam sem Postgres."""
    session = FakeSession()
    context = SimpleNamespace(db_session=session, get_or_create_session=lambda: session)
    monkeypatch.setattr(base_controller, "get_context", lambda: context)
    return session
