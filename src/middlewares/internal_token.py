import hmac

from starlette.responses import JSONResponse

from constants import BYPASS_ENDPOINTS, INTERNAL_TOKEN
from errors.base_error import ForbiddenNotInternal
from errors.handlers import qi_exception_to_response


class InternalTokenMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        method = scope.get("method", "GET")
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        if method == "OPTIONS" or path in BYPASS_ENDPOINTS:
            await self.app(scope, receive, send)
            return
        supplied = headers.get(b"internal-token", b"")
        expected = (INTERNAL_TOKEN or "").encode("utf-8")
        if not hmac.compare_digest(supplied, expected):
            response = qi_exception_to_response(ForbiddenNotInternal())
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def register_internal_token_middleware(application) -> None:
    application.add_middleware(InternalTokenMiddleware)
