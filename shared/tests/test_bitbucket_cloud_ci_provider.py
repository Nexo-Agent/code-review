from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coreview_shared.ci.bitbucket_cloud import BitbucketCloudCIProvider
from coreview_shared.ci.bitbucket_dc import BitbucketDataCenterCIProvider


@pytest.mark.asyncio
async def test_bitbucket_cloud_ci_statuses() -> None:
    provider = BitbucketCloudCIProvider(token="token")
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "values": [{"name": "pipeline", "state": "SUCCESSFUL"}],
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=response):
        summary = await provider.get_ci_summary("acme/backend", "abc123")

    assert summary == "- pipeline: SUCCESSFUL"


@pytest.mark.asyncio
async def test_bitbucket_cloud_ci_not_found() -> None:
    provider = BitbucketCloudCIProvider(token="token")
    response = MagicMock()
    response.status_code = 404

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=response):
        summary = await provider.get_ci_summary("acme/backend", "abc123")

    assert summary == "No CI checks found."


@pytest.mark.asyncio
async def test_bitbucket_dc_ci_builds() -> None:
    provider = BitbucketDataCenterCIProvider(
        token="token",
        base_url="https://bitbucket.example.com",
    )
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "values": [{"name": "Build", "state": "FAILED"}],
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=response):
        summary = await provider.get_ci_summary("ACME/backend", "abc123")

    assert summary == "- Build: FAILED"
