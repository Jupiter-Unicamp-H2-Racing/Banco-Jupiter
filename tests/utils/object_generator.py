from tests.utils.requisition import BaseConnectorResponse
from tests.utils.payload_generator import PayloadGenerator
from tests.utils.request_generator import RequestGenerator


class ObjectGenerator:
    @staticmethod
    def create_customer(hello: str = None) -> BaseConnectorResponse:

        customer_payload = PayloadGenerator.create_customer_payload(hello=hello)

        status, response = RequestGenerator.POST_customer(customer_payload)
        assert status == 201

        return response

    @staticmethod
    def update_customer(customer_key, new_status: str = None) -> BaseConnectorResponse:

        customer_payload = PayloadGenerator.create_new_status_payload(new_status)

        status, response = RequestGenerator.PUT_customer(customer_key, customer_payload)
        assert status == 202

        return response
