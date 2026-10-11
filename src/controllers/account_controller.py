from sqlalchemy.orm import Session
from uuid import uuid4

from controllers.base_controller import BaseController
from dtos.account_dto import AccountDTO
from errors.custom_errors import AccountNotFound, CustomerNotActive, NotFoundCustomer
from models.customer_status import CustomerStatus
from repositories.account_repository import AccountRepository
from repositories.customer_repository import CustomerRepository


class AccountController(BaseController):
    def __init__(self, session: Session) -> None:
        super().__init__(session, __name__)
        self.account_repository = AccountRepository(session)
        self.customer_repository = CustomerRepository(session)

    def create(self, payload: dict) -> dict:
        payload = {**payload, "customer_key": payload["customer_key"].lower()}
        customer = self.customer_repository.get_by_key(payload["customer_key"])
        if customer is None:
            raise NotFoundCustomer(payload["customer_key"])
        if customer.status.enumerator != CustomerStatus.ACTIVE:
            raise CustomerNotActive(customer.customer_key, customer.status.enumerator)
        account = self.account_repository.create(
            customer.id, 0, str(uuid4())
        )
        self.session.commit()
        return AccountDTO.only_obj_key(account)

    def get_by_key(self, account_key: str) -> dict:
        account_key = account_key.lower()
        account = self.account_repository.get_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        return AccountDTO.obj_to_dict(account)
