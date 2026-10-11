import pytest

from tests.utils.db_utils import DbUtils


@pytest.fixture(scope="session", autouse=True)
def fresh_database():
    """Recria o schema pelo Alembic uma vez, antes dos testes de integracao.

    Sem isso, o primeiro teste roda contra o que sobrou de uma execucao
    anterior (ou de um volume antigo do Postgres).
    """
    DbUtils.rollback()
