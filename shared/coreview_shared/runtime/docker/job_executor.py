from __future__ import annotations

import asyncio
import logging
from typing import Any

from docker import DockerClient
from docker.errors import NotFound
from docker.models.containers import Container

from coreview_shared.runtime.review_job import REVIEW_ID_LABEL
from coreview_shared.runtime.specs import JobResult, JobSpec, VolumeMount

logger = logging.getLogger(__name__)


def _volumes_to_docker(volumes: tuple[VolumeMount, ...]) -> dict[str, dict[str, str]]:
    docker_volumes: dict[str, dict[str, str]] = {}
    for mount in volumes:
        if mount.kind != "bind":
            msg = f"Docker runtime only supports bind mounts, got {mount.kind!r}"
            raise ValueError(msg)
        docker_volumes[mount.source] = {
            "bind": mount.target,
            "mode": "ro" if mount.read_only else "rw",
        }
    return docker_volumes


def _stream_container_logs(container: Container) -> None:
    for chunk in container.logs(stream=True, follow=True):
        line = chunk.decode("utf-8", errors="replace").rstrip()
        if line:
            logger.info("[agent] %s", line)


class DockerJobExecutor:
    def __init__(self, client: DockerClient) -> None:
        self._client = client

    async def run(self, spec: JobSpec) -> JobResult:
        return await asyncio.to_thread(self._run_sync, spec)

    async def cleanup_stale(self, labels: dict[str, str]) -> None:
        await asyncio.to_thread(self._cleanup_stale_sync, labels)

    def _cleanup_stale_sync(self, labels: dict[str, str]) -> None:
        review_id = labels.get(REVIEW_ID_LABEL)
        if not review_id:
            return
        containers = self._client.containers.list(
            all=True,
            filters={"label": f"{REVIEW_ID_LABEL}={review_id}"},
        )
        for container in containers:
            logger.warning(
                "Removing stale agent container %s for review %s",
                container.short_id,
                review_id,
            )
            try:
                container.remove(force=True)
            except NotFound:
                pass

    def _run_sync(self, spec: JobSpec) -> JobResult:
        run_kwargs: dict[str, Any] = {
            "image": spec.image,
            "command": spec.command,
            "detach": True,
            "remove": False,
            "stdout": True,
            "stderr": True,
            "volumes": _volumes_to_docker(spec.volumes),
            "environment": spec.environment,
            "labels": spec.labels,
        }
        if spec.network:
            run_kwargs["network"] = spec.network
        elif spec.extra_hosts:
            run_kwargs["extra_hosts"] = spec.extra_hosts

        logger.info(
            "Running review agent container for %s (image=%s)",
            spec.job_id,
            spec.image,
        )

        container: Container | None = None
        try:
            container = self._client.containers.run(**run_kwargs)
            if spec.stream_logs:
                _stream_container_logs(container)
            result = container.wait()
            exit_code = int(result.get("StatusCode", 1))
            log_tail = ""
            if exit_code != 0:
                log_tail = (
                    container.logs(tail=30).decode("utf-8", errors="replace").strip()
                )
            return JobResult(exit_code=exit_code, log_tail=log_tail)
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except NotFound:
                    pass
                except Exception:
                    logger.exception(
                        "Failed to remove agent container for review %s",
                        spec.job_id,
                    )
