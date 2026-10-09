from fastapi import FastAPI
from constants import check_variables
from errors import register_error_handlers
from errors.base_error import error_verification
from middlewares import (register_internal_token_middleware, register_request_context_middleware,
                         register_request_logger_middleware, register_session_manager_middleware)
from resources import HealthCheckResource, TransactionResource, CustomerResource
from utils.logger import setup_logging


def create_app() -> FastAPI:
    application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    register_session_manager_middleware(application)
    register_internal_token_middleware(application)
    register_request_logger_middleware(application)
    register_request_context_middleware(application)
    health = HealthCheckResource()
    customers = CustomerResource()
    transactions = TransactionResource()
    application.add_api_route("/", health.on_get_home, methods=["GET"])
    application.add_api_route("/health_check", health.on_get_health_check, methods=["GET"])
    application.add_api_route("/customers", customers.on_post, methods=["POST"])
    application.add_api_route("/customers", customers.on_get_list, methods=["GET"])
    application.add_api_route("/customers/{customer_key}", customers.on_get_by_key, methods=["GET"])
    application.add_api_route("/customers/{customer_key}", customers.on_put_by_key, methods=["PUT"])
    application.add_api_route("/accounts/{account_key}/transactions", transactions.on_post, methods=["POST"])
    register_error_handlers(application)
    return application


def main() -> FastAPI:
    check_variables()
    error_verification()
    setup_logging()
    return create_app()

app = main()
