from errors.base_error import InternalError
from errors.handlers import qi_exception_to_response
from utils.request_context import REQUEST_ID_HEADER, build_request_id, reset_request_id, set_request_id


class RequestContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value.decode("latin-1") for key, value in scope.get("headers", [])}
        request_id = build_request_id(headers.get(REQUEST_ID_HEADER.lower()))
        request_context_token = set_request_id(request_id)
        response_started = False

        async def send_with_request_id(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                response_headers = list(message.get("headers", []))
                response_headers = [
                    (key, value) for key, value in response_headers
                    if key.lower() != REQUEST_ID_HEADER.lower().encode("ascii")
                ]
                response_headers.append((REQUEST_ID_HEADER.lower().encode("ascii"), request_id.encode("ascii")))
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            if response_started:
                raise
            response = qi_exception_to_response(InternalError())
            await response(scope, receive, send_with_request_id)
        finally:
            reset_request_id(request_context_token)


def register_request_context_middleware(application) -> None:
    application.add_middleware(RequestContextMiddleware)
