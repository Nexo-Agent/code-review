import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.exceptions import MaxRetriesExceededError
from coreview_shared.runtime.docker.job_executor import DockerJobExecutor
from coreview_shared.runtime.docker.provider import DockerRuntimeProvider
from coreview_shared.runtime.review_job import (
    REVIEW_WORKSPACES_VOLUME_NAME,
    agent_database_url,
    agent_nano_cpus,
    build_docker_review_job_spec,
)
from coreview_shared.schemas.execution_contracts import (
    CallbackConfig,
    CredentialRefs,
    ExecutionConfig,
    ReviewContext,
    ReviewExecutionRequest,
    RuntimeMetadata,
    SecretRef,
)

from app.config import CodeReviewSettings, Settings
from app.jobs.review import run_review
from app.providers.factory import build_runtime_provider


def _sample_environment() -> dict[str, str]:
    return {
        "COGITO_REVIEW_REPO_FULL_NAME": "org/repo",
        "COGITO_REVIEW_PR_NUMBER": "1",
        "COGITO_REVIEW_HEAD_SHA": "abc",
        "COGITO_REVIEW_GITHUB_TOKEN": "ghp_test",
        "COGITO_REVIEW_LLM_PROVIDER_ID": "openai-compat",
        "COGITO_REVIEW_LLM_BASE_URL": "https://api.example.com/v1",
        "COGITO_REVIEW_LLM_API_TOKEN": "sk-test",
        "COGITO_REVIEW_LLM_MODEL": "gpt-4o",
        "COGITO_REVIEW_OPENCODE_MODEL": "openai-compat/gpt-4o",
        "COGITO_REVIEW_OPENCODE_AGENT": "code-reviewer",
        "COGITO_REVIEW_REVIEW_TIMEOUT_SECONDS": "600",
        "COGITO_REVIEW_OPENCODE_LOG_LEVEL": "INFO",
        "COGITO_REVIEW_WORKSPACE_ROOT": "/workspaces",
        "COGITO_REVIEW_REVIEW_ID": "550e8400-e29b-41d4-a716-446655440000",
        "COGITO_REVIEW_CALLBACK_URL": "http://api:8000/api/v1/agent/review-events",
        "COGITO_REVIEW_CALLBACK_SECRET": "dev-callback-secret",
        "COGITO_REVIEW_CALLBACK_METADATA": "{}",
        "PYTHONUNBUFFERED": "1",
    }


def _sample_request() -> ReviewExecutionRequest:
    return ReviewExecutionRequest(
        review_id="550e8400-e29b-41d4-a716-446655440000",
        review=ReviewContext(
            repo_full_name="org/repo",
            pr_number=1,
            head_sha="abc",
            git_provider="github",
        ),
        callback=CallbackConfig(
            url="http://api:8000/api/v1/agent/review-events",
            secret_ref=SecretRef(name="review-callback", key="secret"),
        ),
        config=ExecutionConfig(
            workspace_root="/workspaces",
            opencode_agent="code-reviewer",
            opencode_log_level="INFO",
            review_timeout_seconds=600,
            llm_provider_id="openai-compat",
            llm_base_url="https://api.example.com/v1",
            llm_model="gpt-4o",
            opencode_model="openai-compat/gpt-4o",
        ),
        credentials=CredentialRefs(
            git_credential_ref=SecretRef(name="inline", key="git"),
            llm_credential_ref=SecretRef(name="inline", key="llm"),
        ),
        runtime_metadata=RuntimeMetadata(),
        resolved_secret_env={
            "COGITO_REVIEW_GITHUB_TOKEN": "ghp_test",
            "COGITO_REVIEW_LLM_API_TOKEN": "sk-test",
            "COGITO_REVIEW_CALLBACK_SECRET": "dev-callback-secret",
        },
    )


def test_agent_database_url_rewrites_localhost_for_host_gateway() -> None:
    url = agent_database_url(
        "postgresql://app:app@localhost:5432/app",
        network=None,
    )
    assert "@host.docker.internal:" in url


def test_agent_database_url_unchanged_on_compose_network() -> None:
    url = "postgresql://app:app@postgres:5432/app"
    assert agent_database_url(url, network="coreview") == url


def test_build_docker_review_job_spec_network_and_labels() -> None:
    spec = build_docker_review_job_spec(
        review_id="550e8400-e29b-41d4-a716-446655440000",
        agent_image="cogito-review-agent:test",
        environment=_sample_environment(),
        agent_network="coreview",
    )

    assert spec.image == "cogito-review-agent:test"
    assert spec.command == [
        "cogito-review-agent",
        "review",
        "run",
        "--review-id",
        "550e8400-e29b-41d4-a716-446655440000",
    ]
    assert spec.network == "coreview"
    assert spec.extra_hosts is None
    assert len(spec.volumes) == 1
    assert spec.volumes[0].source == REVIEW_WORKSPACES_VOLUME_NAME
    assert spec.volumes[0].target == "/workspaces"
    assert spec.volumes[0].kind == "named"
    assert (
        spec.labels["nexo.coreview.review_id"] == "550e8400-e29b-41d4-a716-446655440000"
    )
    assert spec.environment["COGITO_REVIEW_GITHUB_TOKEN"] == "ghp_test"


def test_build_docker_review_job_spec_resource_limits() -> None:
    spec = build_docker_review_job_spec(
        review_id="r1",
        agent_image="img",
        environment=_sample_environment(),
        agent_network="coreview",
        agent_mem_limit="1g",
        agent_cpus=1.0,
    )

    assert spec.mem_limit == "1g"
    assert spec.nano_cpus == agent_nano_cpus(1.0)


def test_build_docker_review_job_spec_no_resource_limits_when_unset() -> None:
    spec = build_docker_review_job_spec(
        review_id="r1",
        agent_image="img",
        environment=_sample_environment(),
        agent_network="coreview",
        agent_mem_limit="",
        agent_cpus=0.0,
    )

    assert spec.mem_limit is None
    assert spec.nano_cpus is None


def test_build_docker_review_job_spec_extra_hosts_without_network() -> None:
    spec = build_docker_review_job_spec(
        review_id="r1",
        agent_image="img",
        environment=_sample_environment(),
        agent_network=None,
    )

    assert spec.network is None
    assert spec.extra_hosts == {"host.docker.internal": "host-gateway"}


@pytest.mark.asyncio
async def test_docker_job_executor_runs_container() -> None:
    spec = build_docker_review_job_spec(
        review_id="550e8400-e29b-41d4-a716-446655440000",
        agent_image="cogito-review-agent:test",
        environment=_sample_environment(),
        agent_network="coreview",
        agent_mem_limit="1g",
        agent_cpus=1.0,
    )

    mock_client = MagicMock()
    mock_client.containers.list.return_value = []
    mock_container = MagicMock()
    mock_container.logs.side_effect = [
        iter([b"Review completed.\n"]),
        b"",
    ]
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_client.containers.run.return_value = mock_container

    executor = DockerJobExecutor(mock_client)
    await executor.cleanup_stale(spec.labels)
    result = await executor.run(spec)

    assert result.exit_code == 0
    mock_client.containers.list.assert_called_once()
    mock_client.containers.run.assert_called_once()
    run_kwargs = mock_client.containers.run.call_args.kwargs
    assert run_kwargs["image"] == "cogito-review-agent:test"
    assert run_kwargs["command"] == spec.command
    assert run_kwargs["network"] == "coreview"
    assert run_kwargs["detach"] is True
    assert run_kwargs["remove"] is False
    assert run_kwargs["mem_limit"] == "1g"
    assert run_kwargs["memswap_limit"] == "1g"
    assert run_kwargs["nano_cpus"] == agent_nano_cpus(1.0)
    mock_container.wait.assert_called_once()
    mock_container.remove.assert_called_once_with(force=True)


@pytest.mark.asyncio
async def test_docker_runtime_provider_raises_on_nonzero_exit() -> None:
    provider = DockerRuntimeProvider(
        workspace_root="/workspaces",
        agent_image="cogito-review-agent:test",
        agent_network="coreview",
        database_url="postgresql://app:app@postgres:5432/app",
    )

    mock_executor = AsyncMock()
    mock_executor.cleanup_stale = AsyncMock()
    mock_executor.run = AsyncMock(return_value=MagicMock(exit_code=1, log_tail="boom"))

    with patch.object(provider, "_get_job_executor", return_value=mock_executor):
        with pytest.raises(RuntimeError, match="exit 1"):
            await provider.submit_execution(_sample_request())


@patch("coreview_shared.runtime.docker.provider.get_docker_client")
def test_build_providers_docker_runtime(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value = MagicMock()
    runtime = build_runtime_provider(
        infra=CodeReviewSettings(runtime_provider="docker"),
        app_settings=Settings(),
    )
    assert isinstance(runtime, DockerRuntimeProvider)


def test_run_review_marks_failed_after_final_retry() -> None:
    review_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_self = MagicMock()
    mock_self.retry.side_effect = MaxRetriesExceededError()
    mark_failed = AsyncMock()

    def fake_run_db(coro):
        if coro.cr_code.co_name == "dispatch_review_job":
            coro.close()
            raise RuntimeError("boom")
        return asyncio.run(coro)

    with (
        patch("app.jobs.review.run_db", side_effect=fake_run_db),
        patch("app.jobs.review._mark_review_failed", mark_failed),
    ):
        with pytest.raises(MaxRetriesExceededError):
            run_review.run.__func__(mock_self, review_id)

    mock_self.retry.assert_called_once()
    mark_failed.assert_awaited_once_with(review_id, "boom")
