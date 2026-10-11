"""Fluxos de cliente: cadastro, consulta, listagem com filtros e mudança de status."""
from datetime import date
from uuid import uuid4

import pytest

from tests.utils.db_utils import DbUtils
from tests.utils.object_generator import ObjectGenerator
from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator
from tests.utils.request_generator import RequestGenerator

pytestmark = pytest.mark.integration


def _years_ago(years: int) -> str:
    today = date.today()
    return today.replace(year=today.year - years, day=1).isoformat()


def test_create_customer_returns_201_with_only_the_key_and_starts_pending_kyc():
    status, body = RequestGenerator.POST_customer(PayloadGenerator.create_customer_payload())
    assert status == 201
    assert list(body) == ["customer_key"]

    status, customer = RequestGenerator.GET_customer(body["customer_key"])
    assert status == 200
    assert customer["status"] == "pending_kyc"
    assert [event["status"] for event in customer["status_events"]] == ["pending_kyc"]
    assert "id" not in customer


@pytest.mark.parametrize("field,value", [
    ("email", "sem-arroba"),
    ("document_number", "52998224725"),
    ("birthdate", "17/05/1990"),
    ("name", ""),
])
def test_create_customer_rejects_malformed_fields_with_400(field, value):
    payload = PayloadGenerator.create_customer_payload()
    payload[field] = value
    status, _ = RequestGenerator.POST_customer(payload)
    assert status == 400


def test_create_customer_rejects_missing_and_extra_fields():
    payload = PayloadGenerator.create_customer_payload()
    del payload["email"]
    assert RequestGenerator.POST_customer(payload)[0] == 400
    payload = PayloadGenerator.create_customer_payload()
    payload["extra"] = 1
    assert RequestGenerator.POST_customer(payload)[0] == 400


def test_create_customer_rejects_invalid_cpf_with_422():
    status, body = RequestGenerator.POST_customer(
        PayloadGenerator.create_customer_payload(document_number="111.222.333-44"))
    assert status == 422
    assert body["code"] == "QIT001003"


def test_create_customer_rejects_duplicates():
    cpf = RandomGenerator.generate_cpf()
    email = f"dup.{uuid4()}@exemplo.com.br"
    assert RequestGenerator.POST_customer(PayloadGenerator.create_customer_payload(
        email=email, document_number=cpf))[0] == 201

    status, body = RequestGenerator.POST_customer(PayloadGenerator.create_customer_payload(document_number=cpf))
    assert (status, body["code"]) == (409, "QIT001004")
    status, body = RequestGenerator.POST_customer(PayloadGenerator.create_customer_payload(email=email))
    assert (status, body["code"]) == (409, "QIT001005")


def test_create_customer_enforces_age_limits():
    status, body = RequestGenerator.POST_customer(
        PayloadGenerator.create_customer_payload(birthdate=_years_ago(17)))
    assert (status, body["code"]) == (422, "QIT001006")
    status, body = RequestGenerator.POST_customer(
        PayloadGenerator.create_customer_payload(birthdate=_years_ago(81)))
    assert (status, body["code"]) == (422, "QIT001008")
    assert RequestGenerator.POST_customer(
        PayloadGenerator.create_customer_payload(birthdate=_years_ago(18)))[0] == 201
    assert RequestGenerator.POST_customer(
        PayloadGenerator.create_customer_payload(birthdate=_years_ago(80)))[0] == 201


def test_create_customer_rejects_impossible_and_future_birthdates():
    for birthdate in ("1990-02-30", "2999-01-01"):
        status, body = RequestGenerator.POST_customer(
            PayloadGenerator.create_customer_payload(birthdate=birthdate))
        assert (status, body["code"]) == (422, "QIT001007")


def test_get_customer_404_for_unknown_key():
    status, body = RequestGenerator.GET_customer(str(uuid4()))
    assert (status, body["code"]) == (404, "QIT001001")


def test_update_status_from_pending_kyc_is_accepted_and_recorded_in_history():
    customer_key = ObjectGenerator.create_customer()
    status, body = RequestGenerator.PUT_customer(customer_key, {"status": "active"})
    assert (status, body) == (200, {"customer_key": customer_key})
    _, customer = RequestGenerator.GET_customer(customer_key)
    assert customer["status"] == "active"
    assert [event["status"] for event in customer["status_events"]] == ["pending_kyc", "active"]


def test_update_status_is_final_and_validates_the_target():
    customer_key = ObjectGenerator.create_active_customer()
    status, body = RequestGenerator.PUT_customer(customer_key, {"status": "blocked"})
    assert (status, body["code"]) == (409, "QIT001002")
    assert RequestGenerator.PUT_customer(customer_key, {"status": "pending_kyc"})[0] == 400
    assert RequestGenerator.PUT_customer(customer_key, {"status": "nope"})[0] == 400
    assert RequestGenerator.PUT_customer(str(uuid4()), {"status": "active"})[0] == 404


def test_list_customers_paginates_and_filters():
    DbUtils.rollback()
    names = ["Ana Souza", "Bruno Lima", "Carla Souza"]
    keys = {}
    for name, birth in zip(names, ("1980-01-10", "1990-06-15", "2000-12-25")):
        keys[name] = ObjectGenerator.create_customer(name=name, birthdate=birth)
    ObjectGenerator.update_customer(keys["Bruno Lima"], "active")

    status, body = RequestGenerator.GET_customers({"limit": "2", "page": "1"})
    assert status == 200
    assert len(body["data"]) == 2 and body["is_last_page"] is False
    assert [c["name"] for c in body["data"]] == ["Carla Souza", "Bruno Lima"]
    _, page_two = RequestGenerator.GET_customers({"limit": "2", "page": "2"})
    assert [c["name"] for c in page_two["data"]] == ["Ana Souza"] and page_two["is_last_page"] is True

    assert [c["name"] for c in RequestGenerator.GET_customers({"name": "souza"})[1]["data"]] == [
        "Carla Souza", "Ana Souza"]
    assert [c["name"] for c in RequestGenerator.GET_customers({"status": "active"})[1]["data"]] == ["Bruno Lima"]
    by_birth = RequestGenerator.GET_customers({"birthdate_from": "1985-01-01", "birthdate_to": "1995-01-01"})[1]
    assert [c["name"] for c in by_birth["data"]] == ["Bruno Lima"]
    only = RequestGenerator.GET_customers({"email": "nao-existe@x.com"})[1]
    assert only["data"] == [] and only["is_last_page"] is True


def test_list_customers_validates_query_params():
    assert RequestGenerator.GET_customers({"limit": "0"})[0] == 400
    assert RequestGenerator.GET_customers({"unknown": "1"})[0] == 400
    status, _ = RequestGenerator.GET_customers({"birthdate_from": "2000-01-01", "birthdate_to": "1990-01-01"})
    assert status in (400, 422)


def test_email_is_case_insensitive_and_returned_lowercase():
    email = f"maria.{uuid4()}@example.com"
    payload = PayloadGenerator.create_customer_payload(email=email)
    status, body = RequestGenerator.POST_customer(payload)
    assert status == 201
    assert RequestGenerator.POST_customer({**payload, "email": email.upper()})[0:1] == (409,)
    key = body["customer_key"]
    assert RequestGenerator.GET_customer(key)[1]["email"] == email.lower()
    status, listing = RequestGenerator.GET_customers({"email": email.upper()})
    assert status == 200
    assert any(row["customer_key"] == key for row in listing["data"])


def test_customer_name_only_whitespace_is_rejected():
    payload = PayloadGenerator.create_customer_payload(name="   ")
    assert RequestGenerator.POST_customer(payload)[0] == 400


def test_customer_page_with_huge_integer_is_rejected():
    assert RequestGenerator.GET_customers({"page": "99999999999999999999"})[0] == 400


def test_parallel_status_updates_only_allow_one_transition():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    key = ObjectGenerator.create_customer()
    count = 8
    barrier = Barrier(count)

    def update(status):
        barrier.wait()
        return RequestGenerator.PUT_customer(key, {"status": status})[0]

    with ThreadPoolExecutor(max_workers=count) as pool:
        statuses = list(pool.map(update, ["active", "blocked"] * (count // 2)))
    assert statuses.count(200) == 1
    assert statuses.count(409) == count - 1
    customer = RequestGenerator.GET_customer(key)[1]
    assert len(customer["status_events"]) == 2
    assert customer["status"] in {"active", "blocked"}


def test_parallel_duplicate_customer_registration_never_returns_500():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    for _ in range(5):
        payload = PayloadGenerator.create_customer_payload()
        count = 40
        barrier = Barrier(count)

        def create(_):
            barrier.wait()
            return RequestGenerator.POST_customer(payload)[0]

        with ThreadPoolExecutor(max_workers=count) as pool:
            statuses = list(pool.map(create, range(count)))
        assert statuses.count(201) == 1
        assert statuses.count(409) == count - 1
        assert 500 not in statuses


def test_name_percent_filter_is_literal_not_a_wildcard():
    ObjectGenerator.create_customer()
    status, listing = RequestGenerator.GET_customers({"name": "%"})
    assert status == 200
    assert listing["data"] == []
