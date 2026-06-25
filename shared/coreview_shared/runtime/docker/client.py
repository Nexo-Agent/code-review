import logging
import os
import sys
from pathlib import Path

import docker
from docker import DockerClient

logger = logging.getLogger(__name__)

_client: DockerClient | None = None
_resolved_host: str | None = None


def _unix_socket_path(url: str) -> Path | None:
    if not url.startswith("unix://"):
        return None
    return Path(url.removeprefix("unix://"))


def _socket_candidates() -> list[str]:
    """Fallback Docker Engine URLs when no explicit host is configured."""
    if sys.platform == "win32":
        return ["npipe:////./pipe/docker_engine"]

    home = Path.home()
    return [
        "unix:///var/run/docker.sock",
        f"unix://{home}/.docker/run/docker.sock",
        f"unix://{home}/.docker/desktop/docker.sock",
    ]


def resolve_docker_host(explicit: str | None = None) -> str | None:
    """Return configured Docker URL, or None to use env / auto-detection."""
    if explicit:
        return explicit
    return os.environ.get("DOCKER_HOST") or None


def get_docker_client(host: str | None = None) -> DockerClient:
    """Connect to Docker Engine with cross-platform socket resolution."""
    global _client, _resolved_host
    if _client is not None:
        return _client

    errors: list[str] = []
    configured = resolve_docker_host(host)

    if configured:
        try:
            _client = docker.DockerClient(base_url=configured)
            _client.ping()
            _resolved_host = configured
            logger.debug("Connected to Docker Engine at %s", configured)
            return _client
        except docker.errors.DockerException as exc:
            errors.append(f"{configured}: {exc}")

    if os.environ.get("DOCKER_HOST"):
        try:
            _client = docker.from_env()
            _client.ping()
            _resolved_host = os.environ["DOCKER_HOST"]
            logger.debug("Connected to Docker via DOCKER_HOST=%s", _resolved_host)
            return _client
        except docker.errors.DockerException as exc:
            errors.append(f"DOCKER_HOST ({os.environ['DOCKER_HOST']}): {exc}")

    for url in _socket_candidates():
        socket_path = _unix_socket_path(url)
        if socket_path is not None and not socket_path.exists():
            continue
        try:
            _client = docker.DockerClient(base_url=url)
            _client.ping()
            _resolved_host = url
            logger.info("Connected to Docker Engine at %s (auto-detected)", url)
            return _client
        except docker.errors.DockerException as exc:
            errors.append(f"{url}: {exc}")

    try:
        _client = docker.from_env()
        _client.ping()
        _resolved_host = "default"
        logger.debug("Connected to Docker Engine via docker.from_env() default")
        return _client
    except docker.errors.DockerException as exc:
        errors.append(f"default: {exc}")

    hints = [
        "Set NEXO_COREVIEW_DOCKER_HOST or DOCKER_HOST:",
        "  Linux (native):       unix:///var/run/docker.sock",
        "  macOS Docker Desktop: unix:///var/run/docker.sock or unix://$HOME/.docker/run/docker.sock",
        "  Windows Docker:       npipe:////./pipe/docker_engine",
        "  Docker Desktop Linux: unix://$HOME/.docker/desktop/docker.sock",
        "Or export DOCKER_HOST from your active context:",
        (
            "  export DOCKER_HOST=$(docker context inspect "
            "--format '{{.Endpoints.docker.Host}}')"
        ),
    ]
    if errors:
        detail = "\n".join(f"  - {e}" for e in errors)
    else:
        detail = "  (no endpoints reachable)"
    msg = (
        "Cannot connect to Docker Engine.\nTried:\n"
        + detail
        + "\n\n"
        + "\n".join(hints)
    )
    raise RuntimeError(msg)


def reset_docker_client() -> None:
    """Reset cached client (for tests)."""
    global _client, _resolved_host
    _client = None
    _resolved_host = None
