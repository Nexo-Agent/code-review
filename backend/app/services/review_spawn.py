"""Spawn one-shot review agent containers via Docker."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from docker.errors import ContainerError

from app.config import (
    CodeReviewSettings,
    get_code_review_settings,
    get_settings,
)
from app.providers.runtime.docker_client import get_docker_client

logger = logging.getLogger(__name__)


def _resolve_opencode_config_path(cfg: CodeReviewSettings) -> Path:
    if cfg.opencode_config_path:
        return Path(cfg.opencode_config_path)
    return Path("opencode.generated.json")


def _agent_database_url(database_url: str, *, network: str | None) -> str:
    if network:
        return database_url
    return database_url.replace("@localhost:", "@host.docker.internal:").replace(
        "@127.0.0.1:", "@host.docker.internal:"
    )


def run_review_agent_container(review_id: str) -> None:
    """Run review in a one-shot agent container; raises on non-zero exit."""
    settings = get_settings()
    cfg = get_code_review_settings()
    client = get_docker_client(cfg.docker_host or None)

    config_path = _resolve_opencode_config_path(cfg)
    if not config_path.is_file():
        msg = f"OpenCode config not found: {config_path}"
        raise FileNotFoundError(msg)

    network = (cfg.agent_network or "").strip() or None
    volumes: dict[str, dict[str, str]] = {
        str(config_path.resolve()): {
            "bind": "/config/opencode.json",
            "mode": "ro",
        },
    }

    environment = {
        "DATABASE_URL": _agent_database_url(settings.database_url, network=network),
        "OPENCODE_CONFIG": "/config/opencode.json",
        "NEXO_COREVIEW_WORKSPACE_ROOT": cfg.workspace_root,
        "NEXO_COREVIEW_MCP_BIND_HOST": "127.0.0.1",
        "NEXO_COREVIEW_MCP_SERVER_PORT": "8001",
        "NEXO_COREVIEW_MCP_SERVER_URL": "http://127.0.0.1:8001/sse",
        "NEXO_COREVIEW_OPENCODE_BIND_HOST": "0.0.0.0",
        "NEXO_COREVIEW_OPENCODE_PORT": "4096",
        "NEXO_COREVIEW_OPENCODE_SERVER_PASSWORD": cfg.opencode_server_password,
        "NEXO_COREVIEW_OPENCODE_SERVER_USERNAME": cfg.opencode_server_username,
    }

    run_kwargs: dict[str, Any] = {
        "image": cfg.agent_image,
        "command": ["coreview-agent", "review", "run", "--review-id", review_id],
        "detach": False,
        "remove": True,
        "volumes": volumes,
        "environment": environment,
        "labels": {
            "nexo.coreview.role": "review-agent",
            "nexo.coreview.review_id": review_id,
        },
    }

    if network:
        run_kwargs["network"] = network
    else:
        run_kwargs["extra_hosts"] = {"host.docker.internal": "host-gateway"}

    timeout = cfg.review_timeout_seconds + 180

    logger.info(
        "Running review agent container for %s (image=%s)",
        review_id,
        cfg.agent_image,
    )
    try:
        client.containers.run(**run_kwargs, timeout=timeout)
    except ContainerError as exc:
        msg = f"Review agent container failed (exit {exc.exit_status})"
        raise RuntimeError(msg) from exc

    logger.info("Review agent container for %s exited successfully", review_id)
