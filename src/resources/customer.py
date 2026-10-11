from fastapi import Depends, Request
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from controllers.customer_controller import CustomerController
from database import get_db
from utils.schema_handler import SchemaHandler


class CustomerResource:
    @SchemaHandler.validate("post_customer.json")
    def on_post(self, payload: dict, db=Depends(get_db)) -> JSONResponse:
        result = CustomerController(db).create(payload)
        return JSONResponse(content=jsonable_encoder(result), status_code=http_status.HTTP_201_CREATED)

    def on_get_by_key(self, customer_key: str, db=Depends(get_db)) -> JSONResponse:
        result = CustomerController(db).get_by_key(customer_key)
        return JSONResponse(content=jsonable_encoder(result), status_code=http_status.HTTP_200_OK)

    @SchemaHandler.validate("put_customer.json")
    def on_put_by_key(self, customer_key: str, payload: dict, db=Depends(get_db)) -> JSONResponse:
        result = CustomerController(db).update_status(customer_key, payload["status"])
        return JSONResponse(content=jsonable_encoder(result), status_code=http_status.HTTP_200_OK)

    @SchemaHandler.validate_query_params("get_customer.json")
    def on_get_list(self, request: Request, db=Depends(get_db)) -> JSONResponse:
        result = CustomerController(db).list_from_query(request.query_params)
        return JSONResponse(content=jsonable_encoder(result), status_code=http_status.HTTP_200_OK)
