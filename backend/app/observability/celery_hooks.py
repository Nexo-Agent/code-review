import logging
import time
from typing import Any

from celery import signals

from app.observability.metrics import CELERY_TASK_DURATION, CELERY_TASKS

logger = logging.getLogger(__name__)

_TASK_START_KEY = "_cogito_metrics_started_at"


def register_celery_signal_handlers() -> None:
    signals.task_prerun.connect(_on_task_prerun)
    signals.task_success.connect(_on_task_success)
    signals.task_failure.connect(_on_task_failure)
    signals.task_retry.connect(_on_task_retry)
    logger.debug("Registered Celery metrics signal handlers")


def _task_name(sender: Any) -> str:
    name = getattr(sender, "name", None)
    return str(name) if name else "unknown"


def _observe_duration(task: Any, task_id: str) -> None:
    request = task.request
    started_at = getattr(request, _TASK_START_KEY, None)
    if started_at is None:
        return
    duration = time.perf_counter() - started_at
    CELERY_TASK_DURATION.labels(task=_task_name(task)).observe(duration)


def _on_task_prerun(
    task_id: str,
    task: Any,
    *args: Any,
    **kwargs: Any,
) -> None:
    task.request.__dict__[_TASK_START_KEY] = time.perf_counter()


def _on_task_success(
    sender: Any,
    result: Any,
    **kwargs: Any,
) -> None:
    task_name = _task_name(sender)
    CELERY_TASKS.labels(task=task_name, status="succeeded").inc()
    _observe_duration(sender, kwargs.get("task_id", ""))


def _on_task_failure(
    sender: Any,
    task_id: str,
    exception: BaseException,
    *args: Any,
    **kwargs: Any,
) -> None:
    task_name = _task_name(sender)
    CELERY_TASKS.labels(task=task_name, status="failed").inc()
    _observe_duration(sender, task_id)


def _on_task_retry(
    sender: Any,
    reason: Any,
    **kwargs: Any,
) -> None:
    task_name = _task_name(sender)
    CELERY_TASKS.labels(task=task_name, status="retried").inc()
