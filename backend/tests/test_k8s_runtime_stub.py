import pytest
from coreview_shared.runtime.composite import CompositeRuntimeProvider
from coreview_shared.runtime.k8s.provider import K8sRuntimeProvider
from coreview_shared.runtime.specs import ReviewJobRequest

from app.config import CodeReviewSettings, Settings
from app.providers.factory import build_execution_backend, build_runtime_provider


@pytest.mark.asyncio
async def test_k8s_runtime_run_review_job_raises() -> None:
    provider = K8sRuntimeProvider(
        workspace_root="/workspaces",
        database_url="postgresql://app:app@db:5432/app",
    )
    with pytest.raises(NotImplementedError, match="submit_execution"):
        await provider.run_review_job(
            ReviewJobRequest(review_id="r1", environment={"DATABASE_URL": "x"}),
        )


def test_k8s_runtime_command_runner_raises() -> None:
    provider = K8sRuntimeProvider(workspace_root="/workspaces")
    with pytest.raises(NotImplementedError, match="command_runner"):
        provider.command_runner()


def test_provider_factory_k8s_runtime() -> None:
    runtime = build_runtime_provider(
        infra=CodeReviewSettings(runtime_provider="k8s"),
        app_settings=Settings(),
    )
    assert isinstance(runtime, CompositeRuntimeProvider)
    backend = build_execution_backend(
        infra=CodeReviewSettings(runtime_provider="k8s"),
        app_settings=Settings(),
    )
    assert backend.__class__.__name__ == "KubernetesExecutionBackend"
