import time
from urllib.parse import parse_qsl, urlencode

from constants import BYPASS_ENDPOINTS
from utils.logger import get_logger

logger = get_logger(__name__)


class RequestLoggerMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        method = scope.get("method", "GET")
        path = scope.get("path", "")
        query = scope.get("query_string", b"").decode("latin-1")
        bypass = path in BYPASS_ENDPOINTS
        log_path = path
        if query and not bypass:
            masked = urlencode([(key, "***") for key, _ in parse_qsl(query, keep_blank_values=True)])
            log_path = f"{path}?{masked}"
        started_at = time.perf_counter()
        status_code = 500
        if not bypass:
            logger.info("ENTROU %s %s", method, log_path)

        async def send_with_status(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        finally:
            if not bypass or status_code >= 400:
                elapsed_ms = (time.perf_counter() - started_at) * 1000
                logger.info("SAIU %s %s %s - %.1f ms", status_code, method, path, elapsed_ms)


def register_request_logger_middleware(application) -> None:
    application.add_middleware(RequestLoggerMiddleware)
