from sqlalchemy.orm import Session
from datetime import date, datetime, timezone
from uuid import uuid4
from constants import FEE_REVENUE_CUSTOMER_KEY
from models import Customer, CustomerStatus, CustomerStatusEvent


class CustomerRepository:
    _status_ids: dict[str, int] | None = None

    @classmethod
    def reset_status_cache(cls) -> None:
        cls._status_ids = None

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, customer_data: dict) -> Customer:
        status_id = self.get_status_id(CustomerStatus.PENDING_KYC)
        customer = Customer(
            customer_key=str(uuid4()), name=customer_data["name"], email=customer_data["email"].strip().lower(),
            document_number=customer_data["document_number"],
            birthdate=date.fromisoformat(customer_data["birthdate"]), status_id=status_id,
        )
        self.session.add(customer)
        self.session.flush()
        customer.status_events.append(CustomerStatusEvent(status_id=status_id, event_datetime=datetime.now(timezone.utc)))
        return customer

    def get_by_key_for_update(self, customer_key: str):
        return (self.session.query(Customer)
                .filter(Customer.customer_key == customer_key)
                .with_for_update().populate_existing().first())

    def update_status(self, customer: Customer, new_status_enumerator: str) -> None:
        status_id = self.get_status_id(new_status_enumerator)
        customer.status_id = status_id
        customer.status_events.append(CustomerStatusEvent(status_id=status_id, event_datetime=datetime.now(timezone.utc)))

    def get_by_key(self, customer_key: str):
        return self.session.query(Customer).filter(Customer.customer_key == customer_key).first()

    def get_by_document_number(self, document_number: str):
        return self.session.query(Customer).filter(Customer.document_number == document_number).first()

    def get_by_email(self, email: str):
        return self.session.query(Customer).filter(Customer.email == email.strip().lower()).first()

    def get_status_id(self, enumerator: str) -> int:
        if CustomerRepository._status_ids is None:
            rows = self.session.query(CustomerStatus.id, CustomerStatus.enumerator).all()
            CustomerRepository._status_ids = {name: status_id for status_id, name in rows}
        try:
            return CustomerRepository._status_ids[enumerator]
        except KeyError as exc:
            raise LookupError(f"Unknown customer status: {enumerator}") from exc

    def list_page(self, limit: int, offset: int, filters: dict) -> list:
        query = self.session.query(Customer).filter(Customer.customer_key != FEE_REVENUE_CUSTOMER_KEY)
        statuses = filters.get("status_enumerators")
        if statuses:
            query = query.join(Customer.status).filter(CustomerStatus.enumerator.in_(statuses))
        for key in ("name", "email", "document_number"):
            value = filters.get(key)
            if value is not None:
                if key == "name":
                    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                    query = query.filter(Customer.name.ilike(f"%{escaped}%", escape="\\"))
                elif key == "email":
                    query = query.filter(Customer.email == value.strip().lower())
                else:
                    query = query.filter(Customer.document_number == value)
        if filters.get("birthdate_from") is not None:
            query = query.filter(Customer.birthdate >= filters["birthdate_from"])
        if filters.get("birthdate_to") is not None:
            query = query.filter(Customer.birthdate <= filters["birthdate_to"])
        return query.order_by(Customer.created_at.desc(), Customer.id.desc()).limit(limit + 1).offset(offset).all()
