import asyncio
import logging
from fastapi import FastAPI
from fastapi.testclient import TestClient

import middlewares.internal_token as internal_token
from middlewares.request_context import register_request_context_middleware
from middlewares.request_logger import register_request_logger_middleware


def make_app(monkeypatch):
    monkeypatch.setattr(internal_token, "INTERNAL_TOKEN", "valid-token")
    app = FastAPI()
    register_request_logger_middleware(app)
    register_request_context_middleware(app)

    @app.get("/customers")
    def list_customers():
        return {"ok": True}

    @app.get("/explode")
    def explode():
        raise RuntimeError("unexpected")

    return app


def test_non_ascii_internal_token_returns_forbidden(monkeypatch):
    monkeypatch.setattr(internal_token, "INTERNAL_TOKEN", "valid-token")
    app = FastAPI()
    internal_token.register_internal_token_middleware(app)
    app.add_api_route("/private", lambda: {"ok": True}, methods=["GET"])

    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1", "method": "GET", "scheme": "http",
        "path": "/private", "raw_path": b"/private", "query_string": b"",
        "root_path": "", "headers": [(b"internal-token", "tôken".encode("latin-1"))],
        "client": ("testclient", 123), "server": ("testserver", 80),
    }
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(app(scope, receive, send))
    response_start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = next(message for message in messages if message["type"] == "http.response.body")

    assert response_start["status"] == 403
    assert b'QIT000002' in response_body["body"]


def test_query_values_are_masked_in_logs(monkeypatch, caplog):
    app = make_app(monkeypatch)
    caplog.set_level(logging.INFO)

    response = TestClient(app).get(
        "/customers?document_number=529.982.247-25&email=a%40b.com&name=Ana",
    )

    assert response.status_code == 200
    output = "\n".join(
        record.getMessage() for record in caplog.records
        if record.name.startswith("bootcamp-api")
    )
    assert "529.982.247-25" not in output
    assert "a@b.com" not in output
    assert "Ana" not in output
    assert "document_number=%2A%2A%2A" in output
    assert "email=%2A%2A%2A" in output
    assert "name=%2A%2A%2A" in output


def test_unexpected_error_returns_request_id_and_logs_exit(monkeypatch, caplog):
    app = make_app(monkeypatch)
    caplog.set_level(logging.INFO)

    response = TestClient(app).get("/explode", headers={"INTERNAL-TOKEN": "valid-token"})

    assert response.status_code == 500
    assert response.headers.get("X-Request-ID")
    assert response.json()["code"] == "QIT000500"
    assert any(record.getMessage().startswith("SAIU 500 GET /explode") for record in caplog.records)
