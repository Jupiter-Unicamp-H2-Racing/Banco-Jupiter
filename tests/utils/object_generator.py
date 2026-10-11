from tests.utils.payload_generator import PayloadGenerator
from tests.utils.request_generator import RequestGenerator


class ObjectGenerator:
    """Cria, pela API, as entidades que os testes precisam como ponto de partida."""

    @staticmethod
    def create_customer(**overrides) -> str:
        status, body = RequestGenerator.POST_customer(PayloadGenerator.create_customer_payload(**overrides))
        assert status == 201, body
        return body["customer_key"]

    @staticmethod
    def update_customer(customer_key: str, new_status: str) -> dict:
        status, body = RequestGenerator.PUT_customer(
            customer_key, PayloadGenerator.create_new_status_payload(new_status)
        )
        assert status == 200, body
        return body

    @staticmethod
    def create_active_customer() -> str:
        customer_key = ObjectGenerator.create_customer()
        ObjectGenerator.update_customer(customer_key, "active")
        return customer_key

    @staticmethod
    def create_account(customer_key: str = None, balance: int = 0) -> str:
        if customer_key is None:
            customer_key = ObjectGenerator.create_active_customer()
        status, body = RequestGenerator.POST_account({"customer_key": customer_key})
        assert status == 201, body
        account_key = body["account_key"]
        if balance:
            from sqlalchemy import create_engine, text
            from tests.utils.db_utils import DbUtils

            engine = create_engine(DbUtils.database_url())
            try:
                with engine.begin() as connection:
                    connection.execute(
                        text("UPDATE account SET balance = :balance WHERE account_key = :key"),
                        {"balance": balance, "key": account_key},
                    )
            finally:
                engine.dispose()
        return account_key
