from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coreview_shared.ci.gitlab import GitLabCIProvider


@pytest.mark.asyncio
async def test_gitlab_ci_summary_from_statuses() -> None:
    provider = GitLabCIProvider(token="token", base_url="https://gitlab.example.com")
    statuses_response = MagicMock()
    statuses_response.status_code = 200
    statuses_response.raise_for_status = MagicMock()
    statuses_response.json.return_value = [
        {"name": "build", "status": "success"},
        {"name": "test", "status": "failed"},
    ]

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = statuses_response
        mock_client_cls.return_value = mock_client

        summary = await provider.get_ci_summary("acme/backend", "abc123")

    assert "- build: success" in summary
    assert "- test: failed" in summary


@pytest.mark.asyncio
async def test_gitlab_ci_summary_falls_back_to_pipelines() -> None:
    provider = GitLabCIProvider(token="token")
    empty_statuses = MagicMock()
    empty_statuses.status_code = 200
    empty_statuses.raise_for_status = MagicMock()
    empty_statuses.json.return_value = []

    pipelines_response = MagicMock()
    pipelines_response.status_code = 200
    pipelines_response.raise_for_status = MagicMock()
    pipelines_response.json.return_value = [{"ref": "main", "status": "running"}]

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = [empty_statuses, pipelines_response]
        mock_client_cls.return_value = mock_client

        summary = await provider.get_ci_summary("acme/backend", "abc123")

    assert "- pipeline/main: running" in summary


@pytest.mark.asyncio
async def test_gitlab_ci_summary_not_found() -> None:
    provider = GitLabCIProvider(token="token")
    not_found = MagicMock()
    not_found.status_code = 404

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = not_found
        mock_client_cls.return_value = mock_client

        summary = await provider.get_ci_summary("acme/backend", "abc123")

    assert summary == "No CI checks found."
