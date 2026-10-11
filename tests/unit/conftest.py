from types import SimpleNamespace

import pytest



class FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@pytest.fixture
def fake_session():
    """Fornece uma sessão falsa aos controllers sem PostgreSQL."""
    return FakeSession()
