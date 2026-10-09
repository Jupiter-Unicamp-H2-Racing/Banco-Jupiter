from typing import List
from models.customer import Customer


class CustomerDTO:
    @staticmethod
    def obj_to_dict(customer: Customer) -> dict:
        result = CustomerDTO.obj_to_simplified_dict(customer)
        result["status_events"] = [
            {"status": event.status.enumerator, "event_datetime": event.event_datetime.isoformat()}
            for event in customer.status_events
        ]
        return result

    @staticmethod
    def obj_to_simplified_dict(customer: Customer) -> dict:
        return {
            "customer_key": customer.customer_key.strip(),
            "name": customer.name,
            "email": customer.email,
            "document_number": customer.document_number,
            "birthdate": customer.birthdate.isoformat(),
            "status": customer.status.enumerator,
        }

    @staticmethod
    def list_obj_to_list_dict(customers_list: List[Customer]) -> List[dict]:
        return [CustomerDTO.obj_to_simplified_dict(customer) for customer in customers_list]

    @staticmethod
    def only_obj_key(customer: Customer) -> dict:
        return {"customer_key": customer.customer_key.strip()}
