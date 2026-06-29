import pytest
from coreview_shared.runtime.k8s.provider import K8sRuntimeProvider

from app.config import CodeReviewSettings, Settings
from app.providers.factory import build_runtime_provider


def test_k8s_runtime_command_runner_raises() -> None:
    provider = K8sRuntimeProvider(workspace_root="/workspaces")
    with pytest.raises(NotImplementedError, match="command_runner"):
        provider.command_runner()


def test_provider_factory_k8s_runtime() -> None:
    runtime = build_runtime_provider(
        infra=CodeReviewSettings(runtime_provider="k8s"),
        app_settings=Settings(),
    )
    assert isinstance(runtime, K8sRuntimeProvider)
