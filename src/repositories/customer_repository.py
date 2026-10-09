from datetime import date, datetime, timezone
from uuid import uuid4
from database import Context
from models import Customer, CustomerStatus, CustomerStatusEvent


class CustomerRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, customer_data: dict) -> Customer:
        status = self.get_status(CustomerStatus.PENDING_KYC)
        customer = Customer(
            customer_key=str(uuid4()), name=customer_data["name"], email=customer_data["email"],
            document_number=customer_data["document_number"],
            birthdate=date.fromisoformat(customer_data["birthdate"]), status=status,
        )
        self.session.add(customer)
        self.session.flush()
        customer.status_events.append(CustomerStatusEvent(status=status, event_datetime=datetime.now(timezone.utc)))
        return customer

    def update_status(self, customer: Customer, new_status_enumerator: str) -> None:
        new_status = self.get_status(new_status_enumerator)
        customer.status = new_status
        customer.status_events.append(CustomerStatusEvent(status=new_status, event_datetime=datetime.now(timezone.utc)))

    def get_by_key(self, customer_key: str):
        return self.session.query(Customer).filter(Customer.customer_key == customer_key).first()

    def get_by_document_number(self, document_number: str):
        return self.session.query(Customer).filter(Customer.document_number == document_number).first()

    def get_by_email(self, email: str):
        return self.session.query(Customer).filter(Customer.email == email).first()

    def get_status(self, enumerator: str) -> CustomerStatus:
        return self.session.query(CustomerStatus).filter(CustomerStatus.enumerator == enumerator).one()

    def list_page(self, limit: int, offset: int, filters: dict) -> list:
        query = self.session.query(Customer)
        statuses = filters.get("status_enumerators")
        if statuses:
            query = query.join(Customer.status).filter(CustomerStatus.enumerator.in_(statuses))
        for key in ("name", "email", "document_number"):
            value = filters.get(key)
            if value is not None:
                query = query.filter(getattr(Customer, key).ilike(f"%{value}%") if key == "name" else getattr(Customer, key) == value)
        if filters.get("birthdate_from") is not None:
            query = query.filter(Customer.birthdate >= filters["birthdate_from"])
        if filters.get("birthdate_to") is not None:
            query = query.filter(Customer.birthdate <= filters["birthdate_to"])
        return query.order_by(Customer.created_at.desc(), Customer.id.desc()).limit(limit + 1).offset(offset).all()
