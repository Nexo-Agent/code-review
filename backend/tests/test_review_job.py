from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import CodeReviewSettings, Settings
from app.providers.factory import build_providers
from app.providers.runtime.docker.job_executor import DockerJobExecutor
from app.providers.runtime.docker.provider import DockerRuntimeProvider
from app.providers.runtime.review_job import (
    agent_database_url,
    build_docker_review_job_spec,
    resolve_opencode_config_path,
)
from app.providers.runtime.specs import ReviewJobRequest


def test_agent_database_url_rewrites_localhost_for_host_gateway() -> None:
    url = agent_database_url(
        "postgresql://app:app@localhost:5432/app",
        network=None,
    )
    assert "@host.docker.internal:" in url


def test_agent_database_url_unchanged_on_compose_network() -> None:
    url = "postgresql://app:app@postgres:5432/app"
    assert agent_database_url(url, network="coreview") == url


def test_build_docker_review_job_spec_network_and_labels(tmp_path) -> None:
    config_file = tmp_path / "opencode.generated.json"
    config_file.write_text("{}\n", encoding="utf-8")

    spec = build_docker_review_job_spec(
        review_id="550e8400-e29b-41d4-a716-446655440000",
        agent_image="nexo-coreview-agent:test",
        workspace_root="/workspaces",
        database_url="postgresql://app:app@postgres:5432/app",
        opencode_config_path=config_file,
        opencode_config_host_path=None,
        agent_network="coreview",
    )

    assert spec.image == "nexo-coreview-agent:test"
    assert spec.command == [
        "coreview-agent",
        "review",
        "run",
        "--review-id",
        "550e8400-e29b-41d4-a716-446655440000",
    ]
    assert spec.network == "coreview"
    assert spec.extra_hosts is None
    assert (
        spec.labels["nexo.coreview.review_id"] == "550e8400-e29b-41d4-a716-446655440000"
    )
    assert spec.environment["DATABASE_URL"] == "postgresql://app:app@postgres:5432/app"


def test_build_docker_review_job_spec_extra_hosts_without_network(tmp_path) -> None:
    config_file = tmp_path / "opencode.generated.json"
    config_file.write_text("{}\n", encoding="utf-8")

    spec = build_docker_review_job_spec(
        review_id="r1",
        agent_image="img",
        workspace_root="/workspaces",
        database_url="postgresql://app:app@localhost:5432/app",
        opencode_config_path=config_file,
        opencode_config_host_path=None,
        agent_network=None,
    )

    assert spec.network is None
    assert spec.extra_hosts == {"host.docker.internal": "host-gateway"}
    assert "@host.docker.internal:" in spec.environment["DATABASE_URL"]


@pytest.mark.asyncio
async def test_docker_job_executor_runs_container(tmp_path) -> None:
    config_file = tmp_path / "opencode.generated.json"
    config_file.write_text("{}\n", encoding="utf-8")

    spec = build_docker_review_job_spec(
        review_id="550e8400-e29b-41d4-a716-446655440000",
        agent_image="nexo-coreview-agent:test",
        workspace_root="/workspaces",
        database_url="postgresql://app:app@postgres:5432/app",
        opencode_config_path=config_file,
        opencode_config_host_path=None,
        agent_network="coreview",
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
    assert run_kwargs["image"] == "nexo-coreview-agent:test"
    assert run_kwargs["command"] == spec.command
    assert run_kwargs["network"] == "coreview"
    assert run_kwargs["detach"] is True
    assert run_kwargs["remove"] is False
    mock_container.wait.assert_called_once()
    mock_container.remove.assert_called_once_with(force=True)


@pytest.mark.asyncio
async def test_docker_runtime_provider_raises_on_nonzero_exit(tmp_path) -> None:
    config_file = tmp_path / "opencode.generated.json"
    config_file.write_text("{}\n", encoding="utf-8")

    provider = DockerRuntimeProvider(
        workspace_root="/workspaces",
        agent_image="nexo-coreview-agent:test",
        agent_network="coreview",
        opencode_config_path=str(config_file),
        database_url="postgresql://app:app@postgres:5432/app",
    )

    mock_executor = AsyncMock()
    mock_executor.cleanup_stale = AsyncMock()
    mock_executor.run = AsyncMock(return_value=MagicMock(exit_code=1, log_tail="boom"))

    with patch.object(provider, "_get_job_executor", return_value=mock_executor):
        with pytest.raises(RuntimeError, match="exit 1"):
            await provider.run_review_job(
                ReviewJobRequest(review_id="r1"),
            )


def test_resolve_opencode_config_path_default() -> None:
    assert resolve_opencode_config_path("") == Path("opencode.generated.json")


@patch("app.providers.runtime.docker.provider.get_docker_client")
def test_build_providers_docker_runtime(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value = MagicMock()
    providers = build_providers(
        CodeReviewSettings(
            git_provider="github",
            runtime_provider="docker",
        ),
        app_settings=Settings(),
    )
    assert providers.runtime.command_runner() is not None
