from unittest.mock import MagicMock, patch

from app.config import CodeReviewSettings, Settings
from app.services import review_spawn


def test_agent_database_url_rewrites_localhost_for_host_gateway() -> None:
    url = review_spawn._agent_database_url(
        "postgresql://app:app@localhost:5432/app",
        network=None,
    )
    assert "@host.docker.internal:" in url


def test_agent_database_url_unchanged_on_compose_network() -> None:
    url = "postgresql://app:app@postgres:5432/app"
    assert review_spawn._agent_database_url(url, network="coreview") == url


@patch.object(review_spawn, "get_settings")
@patch.object(review_spawn, "get_code_review_settings")
@patch.object(review_spawn, "get_docker_client")
def test_run_review_agent_container_invokes_docker_run(
    mock_get_client: MagicMock,
    mock_get_cfg: MagicMock,
    mock_get_settings: MagicMock,
    tmp_path,
) -> None:
    config_file = tmp_path / "opencode.generated.json"
    config_file.write_text("{}\n", encoding="utf-8")

    mock_get_settings.return_value = Settings(
        database_url="postgresql://app:app@localhost:5432/app"
    )
    mock_get_cfg.return_value = CodeReviewSettings(
        agent_image="nexo-coreview-agent:test",
        agent_network="coreview",
        opencode_config_path=str(config_file),
        review_timeout_seconds=600,
    )

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    review_spawn.run_review_agent_container("550e8400-e29b-41d4-a716-446655440000")

    mock_client.containers.run.assert_called_once()
    run_kwargs = mock_client.containers.run.call_args.kwargs
    assert run_kwargs["image"] == "nexo-coreview-agent:test"
    assert run_kwargs["command"] == [
        "coreview-agent",
        "review",
        "run",
        "--review-id",
        "550e8400-e29b-41d4-a716-446655440000",
    ]
    assert run_kwargs["network"] == "coreview"
    assert run_kwargs["detach"] is False
    assert run_kwargs["remove"] is True
    assert run_kwargs["timeout"] == 780
