import pytest

from app.config import CodeReviewSettings, Settings
from app.providers.factory import build_providers
from app.providers.runtime.k8s.provider import K8sRuntimeProvider
from app.providers.runtime.specs import ReviewJobRequest


@pytest.mark.asyncio
async def test_k8s_runtime_run_review_job_raises() -> None:
    provider = K8sRuntimeProvider(
        workspace_root="/workspaces",
        database_url="postgresql://app:app@db:5432/app",
    )
    with pytest.raises(NotImplementedError, match="K8s runtime not implemented"):
        await provider.run_review_job(
            ReviewJobRequest(review_id="r1", environment={"DATABASE_URL": "x"}),
        )


def test_k8s_runtime_command_runner_raises() -> None:
    provider = K8sRuntimeProvider(workspace_root="/workspaces")
    with pytest.raises(NotImplementedError, match="command_runner"):
        provider.command_runner()


def test_provider_factory_k8s_runtime() -> None:
    providers = build_providers(
        CodeReviewSettings(
            git_provider="github",
            runtime_provider="k8s",
        ),
        app_settings=Settings(),
    )
    assert isinstance(providers.runtime, K8sRuntimeProvider)
