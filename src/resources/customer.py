from fastapi import Request, Response
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from controllers.customer_controller import CustomerController
from utils.schema_handler import SchemaHandler

DEFAULT_LIMIT = 10
DEFAULT_PAGE = 1

class CustomerResource:
    @SchemaHandler.validate("post_customer.json")
    def on_post(self, payload: dict) -> JSONResponse:
        result = CustomerController().create(payload)
        return JSONResponse(content=jsonable_encoder(result), status_code=http_status.HTTP_201_CREATED)

    def on_get_by_key(self, customer_key: str) -> JSONResponse:
        result = CustomerController().get_by_key(customer_key)
        return JSONResponse(content=jsonable_encoder(result), status_code=http_status.HTTP_200_OK)

    @SchemaHandler.validate("put_customer.json")
    def on_put_by_key(self, customer_key: str, payload: dict) -> JSONResponse:
        result = CustomerController().update_status(customer_key, payload["status"])
        return JSONResponse(content=jsonable_encoder(result), status_code=http_status.HTTP_202_ACCEPTED)

    @SchemaHandler.validate_query_params("get_customer.json")
    def on_get_list(self, request: Request) -> JSONResponse:
        params = request.query_params
        limit = int(params.get("limit", DEFAULT_LIMIT))
        page = int(params.get("page", DEFAULT_PAGE))
        filters = {"status_enumerators": params.getlist("status"), "name": params.get("name"),
                   "email": params.get("email"), "document_number": params.get("document_number"),
                   "birthdate_from": params.get("birthdate_from"), "birthdate_to": params.get("birthdate_to")}
        result = CustomerController().get_list(limit, (page - 1) * limit, filters)
        return JSONResponse(content=jsonable_encoder({"data": result["customers_list_dto"], "limit": limit,
                                                       "page": page, "is_last_page": result["is_last_page"]}),
                            status_code=http_status.HTTP_200_OK)
