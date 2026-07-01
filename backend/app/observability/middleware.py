import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.observability.metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS


class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        route = request.scope.get("route")
        handler = route.path if route is not None else "unmatched"
        method = request.method
        status = str(response.status_code)

        HTTP_REQUESTS.labels(
            method=method,
            handler=handler,
            status=status,
        ).inc()
        HTTP_REQUEST_DURATION.labels(method=method, handler=handler).observe(duration)
        return response
