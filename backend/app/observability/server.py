import logging
import threading

from prometheus_client import start_http_server

from app.config import get_code_review_settings

logger = logging.getLogger(__name__)

_started = False
_lock = threading.Lock()


def start_metrics_server_if_enabled() -> None:
    global _started
    settings = get_code_review_settings()
    if not settings.metrics_enabled:
        return

    with _lock:
        if _started:
            return
        start_http_server(
            settings.metrics_bind_port,
            addr=settings.metrics_bind_host,
        )
        _started = True
        logger.info(
            "Prometheus metrics server listening on %s:%s",
            settings.metrics_bind_host,
            settings.metrics_bind_port,
        )
