from fastapi import Depends
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from controllers.account_controller import AccountController
from database import get_db
from utils.schema_handler import SchemaHandler


class AccountResource:
    @SchemaHandler.validate("post_account.json")
    def on_post(self, payload: dict, db=Depends(get_db)) -> JSONResponse:
        result = AccountController(db).create(payload)
        return JSONResponse(content=jsonable_encoder(result), status_code=http_status.HTTP_201_CREATED)

    def on_get_by_key(self, account_key: str, db=Depends(get_db)) -> JSONResponse:
        result = AccountController(db).get_by_key(account_key)
        return JSONResponse(content=jsonable_encoder(result), status_code=http_status.HTTP_200_OK)
