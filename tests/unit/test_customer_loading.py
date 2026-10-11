from models.account import Account
from models.customer import Customer
from models.customer_status import CustomerStatus


def test_customer_status_does_not_eagerly_load_all_customers():
    assert "customers" not in CustomerStatus.__mapper__.relationships


def test_customer_collections_and_account_customer_are_not_eager_by_default():
    assert Customer.__mapper__.relationships["accounts"].lazy != "selectin"
    assert Customer.__mapper__.relationships["status_events"].lazy != "selectin"
    assert Account.__mapper__.relationships["customer"].lazy != "selectin"
