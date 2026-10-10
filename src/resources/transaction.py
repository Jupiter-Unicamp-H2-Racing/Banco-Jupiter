from fastapi import Request
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers.transaction_controller import TransactionController
from utils.schema_handler import SchemaHandler


class TransactionResource:
    @SchemaHandler.validate("post_transaction.json")
    def on_post(
        self,
        account_key: str,
        payload: dict,
        request: Request,
    ) -> JSONResponse:
        idempotency_key = request.headers.get("Idempotency-Key")

        transaction = TransactionController().create(
            account_key,
            payload,
            idempotency_key=idempotency_key,
        )

        return JSONResponse(
            content=jsonable_encoder(transaction),
            status_code=http_status.HTTP_201_CREATED,
        )
    @SchemaHandler.validate_query_params("get_transactions.json")
    def on_get_list(self, account_key: str, request: Request) -> JSONResponse:
        params = request.query_params
        result = TransactionController().list(
            account_key,
            limit=int(params.get("limit", 20)),
            page=int(params.get("page", 1)),
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
        )
        return JSONResponse(content=jsonable_encoder(result), status_code=http_status.HTTP_200_OK)
