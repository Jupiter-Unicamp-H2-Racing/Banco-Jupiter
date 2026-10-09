from datetime import date
from controllers.base_controller import BaseController
from dtos import CustomerDTO
from errors import InvalidParameter
from errors.custom_errors import DuplicatedDocumentNumber, DuplicatedEmail, InvalidBirthdate, InvalidDocumentNumber, NotFoundCustomer, CustomerFinalStatus, UnderageCustomer, OverAgeCustomer
from models.customer import Customer
from models.customer_status import CustomerStatus
from repositories.customer_repository import CustomerRepository
from utils.document_number import is_valid_cpf

MINIMUM_AGE = 18
MAXIMUM_AGE = 80


class CustomerController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.customer_repository = CustomerRepository(self.context)

    def create(self, customer_data: dict) -> dict:
        document_number = customer_data["document_number"]
        email = customer_data["email"]
        birthdate = self._parse_birthdate(customer_data["birthdate"])
        age = self._age_in_years(birthdate)
        if age < MINIMUM_AGE:
            raise UnderageCustomer(age, MINIMUM_AGE)
        if age > MAXIMUM_AGE:
            raise OverAgeCustomer(age, MAXIMUM_AGE)
        if not is_valid_cpf(document_number):
            raise InvalidDocumentNumber(document_number)
        if self.customer_repository.get_by_document_number(document_number):
            raise DuplicatedDocumentNumber(document_number)
        if self.customer_repository.get_by_email(email):
            raise DuplicatedEmail(email)
        customer = self.customer_repository.create(customer_data)
        self.session.commit()
        return CustomerDTO.only_obj_key(customer)

    def get_by_key(self, customer_key: str) -> dict:
        customer = self.customer_repository.get_by_key(customer_key)
        if customer is None:
            raise NotFoundCustomer(customer_key)
        return CustomerDTO.obj_to_dict(customer)

    def get_list(self, limit: int, offset: int, filters: dict) -> dict:
        for key in ("birthdate_from", "birthdate_to"):
            if filters.get(key) is not None:
                filters[key] = self._parse_birthdate(filters[key])
        start, end = filters.get("birthdate_from"), filters.get("birthdate_to")
        if start is not None and end is not None and start > end:
            raise InvalidParameter(f"birthdate_from ({start}) is after birthdate_to ({end})")
        customers = self.customer_repository.list_page(limit, offset, filters)
        is_last_page = len(customers) <= limit
        if not is_last_page:
            customers = customers[:-1]
        return {"customers_list_dto": CustomerDTO.list_obj_to_list_dict(customers), "is_last_page": is_last_page}

    def update_status(self, customer_key: str, new_status: str) -> dict:
        customer = self.customer_repository.get_by_key(customer_key)
        if customer is None:
            raise NotFoundCustomer(customer_key)
        if new_status not in CustomerStatus.ALLOWED or new_status == CustomerStatus.PENDING_KYC:
            raise InvalidParameter(f"Invalid target customer status: {new_status}")
        if customer.status.enumerator != CustomerStatus.PENDING_KYC:
            raise CustomerFinalStatus(customer.status.enumerator, new_status)
        self.customer_repository.update_status(customer, new_status)
        self.session.commit()
        return CustomerDTO.only_obj_key(customer)

    def _parse_birthdate(self, value: str) -> date:
        try:
            parsed = date.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise InvalidBirthdate(value) from exc
        if parsed > date.today():
            raise InvalidBirthdate(value)
        return parsed

    @staticmethod
    def _age_in_years(birthdate: date) -> int:
        today = date.today()
        return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
