from __future__ import annotations

from coreview_shared.runtime.specs import JobSpec

REVIEW_AGENT_ROLE = "review-agent"
REVIEW_ID_LABEL = "nexo.coreview.review_id"
REVIEW_ROLE_LABEL = "nexo.coreview.role"


def agent_database_url(database_url: str, *, network: str | None) -> str:
    if network:
        return database_url
    return database_url.replace("@localhost:", "@host.docker.internal:").replace(
        "@127.0.0.1:", "@host.docker.internal:"
    )


def agent_nano_cpus(agent_cpus: float) -> int | None:
    if agent_cpus <= 0:
        return None
    return int(agent_cpus * 1_000_000_000)


def review_job_labels(review_id: str) -> dict[str, str]:
    return {
        REVIEW_ROLE_LABEL: REVIEW_AGENT_ROLE,
        REVIEW_ID_LABEL: review_id,
    }


def build_docker_review_job_spec(
    *,
    review_id: str,
    agent_image: str,
    environment: dict[str, str],
    agent_network: str | None,
    agent_mem_limit: str = "",
    agent_cpus: float = 0.0,
) -> JobSpec:
    network = (agent_network or "").strip() or None
    mem_limit = agent_mem_limit.strip() or None
    return JobSpec(
        job_id=review_id,
        image=agent_image,
        command=[
            "coreview-agent",
            "review",
            "run",
            "--review-id",
            review_id,
        ],
        environment=environment,
        volumes=(),
        labels=review_job_labels(review_id),
        network=network,
        extra_hosts=None if network else {"host.docker.internal": "host-gateway"},
        mem_limit=mem_limit,
        nano_cpus=agent_nano_cpus(agent_cpus),
    )


def build_k8s_review_job_spec(
    *,
    review_id: str,
    agent_image: str,
    environment: dict[str, str],
    k8s_namespace: str,
) -> JobSpec:
    """Build a K8s-oriented job spec (env-only config; no ConfigMap volume)."""
    return JobSpec(
        job_id=review_id,
        image=agent_image,
        command=[
            "coreview-agent",
            "review",
            "run",
            "--review-id",
            review_id,
        ],
        environment=environment,
        volumes=(),
        labels=review_job_labels(review_id),
        network=k8s_namespace,
    )
