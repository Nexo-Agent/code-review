import json
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.config import CodeReviewSettings
from app.repositories.llm_providers import LlmProviderRow
from app.repositories.repo_integrations import RepoIntegrationRow
from app.repositories.reviews import ReviewRow
from app.services.review_job_prepare import build_agent_environment


def _review_row() -> ReviewRow:
    now = datetime.now(tz=UTC)
    return ReviewRow(
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        provider="github",
        repo_full_name="org/repo",
        pr_number=42,
        pr_title="Fix login bug",
        head_sha="abc123",
        status="pending",
        delivery_id="del-1",
        repo_integration_id=UUID("11111111-1111-1111-1111-111111111111"),
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=now,
    )


def _repo_integration() -> RepoIntegrationRow:
    now = datetime.now(tz=UTC)
    return RepoIntegrationRow(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        name="org/repo",
        git_provider="github",
        repo_full_name="org/repo",
        github_webhook_secret="secret",
        github_token="ghp_test",
        llm_provider_id=UUID("22222222-2222-2222-2222-222222222222"),
        system_prompt="Focus on security only.",
        enabled=True,
        ado_organization="",
        ado_project="",
        ado_pat="",
        ado_webhook_username="",
        ado_webhook_password="",
        created_at=now,
        updated_at=now,
    )


def _llm_provider() -> LlmProviderRow:
    now = datetime.now(tz=UTC)
    return LlmProviderRow(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        name="default",
        provider_id="openai-compat",
        base_url="https://api.example.com/v1",
        api_token="sk-test",
        model="gpt-4o",
        opencode_model="",
        is_default=True,
        created_at=now,
        updated_at=now,
    )


def test_build_agent_environment_includes_review_and_credentials() -> None:
    review = _review_row()
    repo_integration = _repo_integration()
    llm_provider = _llm_provider()
    infra = CodeReviewSettings(
        opencode_agent="code-reviewer",
        review_timeout_seconds=900,
        opencode_log_level="DEBUG",
        workspace_root="/workspaces",
        agent_callback_url="http://api:8000/api/v1/agent/review-events",
        agent_callback_secret="shared-secret",
    )

    env = build_agent_environment(
        review_id=str(review.id),
        review=review,
        repo_integration=repo_integration,
        llm_provider=llm_provider,
        infra=infra,
    )

    assert env["NEXO_COREVIEW_REPO_FULL_NAME"] == "org/repo"
    assert env["NEXO_COREVIEW_PR_NUMBER"] == "42"
    assert env["NEXO_COREVIEW_HEAD_SHA"] == "abc123"
    assert env["NEXO_COREVIEW_GITHUB_TOKEN"] == "ghp_test"
    assert env["NEXO_COREVIEW_LLM_API_TOKEN"] == "sk-test"
    assert env["NEXO_COREVIEW_OPENCODE_MODEL"] == "openai-compat/gpt-4o"
    assert env["NEXO_COREVIEW_REVIEW_TIMEOUT_SECONDS"] == "900"
    assert env["NEXO_COREVIEW_REVIEW_ID"] == str(review.id)
    assert (
        env["NEXO_COREVIEW_CALLBACK_URL"]
        == "http://api:8000/api/v1/agent/review-events"
    )
    assert env["NEXO_COREVIEW_CALLBACK_SECRET"] == "shared-secret"
    assert "DATABASE_URL" not in env

    metadata = json.loads(env["NEXO_COREVIEW_CALLBACK_METADATA"])
    assert metadata["delivery_id"] == "del-1"
    assert metadata["repo_integration_id"] == str(review.repo_integration_id)


def test_build_agent_environment_includes_ado_credentials() -> None:
    review = _review_row()
    repo_integration = replace(
        _repo_integration(),
        git_provider="azure-devops",
        repo_full_name="fabrikam/MyProject/Repo",
        ado_organization="fabrikam",
        ado_project="MyProject",
        ado_pat="ado-pat",
    )
    env = build_agent_environment(
        review_id=str(review.id),
        review=review,
        repo_integration=repo_integration,
        llm_provider=_llm_provider(),
        infra=CodeReviewSettings(
            agent_callback_url="http://api:8000/api/v1/agent/review-events",
            agent_callback_secret="shared-secret",
        ),
    )

    assert env["NEXO_COREVIEW_GIT_PROVIDER"] == "azure-devops"
    assert env["NEXO_COREVIEW_ADO_ORGANIZATION"] == "fabrikam"
    assert env["NEXO_COREVIEW_ADO_PROJECT"] == "MyProject"
    assert env["NEXO_COREVIEW_ADO_PAT"] == "ado-pat"


def test_build_agent_environment_includes_custom_system_prompt() -> None:
    env = build_agent_environment(
        review_id=str(_review_row().id),
        review=_review_row(),
        repo_integration=_repo_integration(),
        llm_provider=_llm_provider(),
        infra=CodeReviewSettings(
            agent_callback_url="http://api:8000/api/v1/agent/review-events",
            agent_callback_secret="shared-secret",
        ),
    )

    assert env["NEXO_COREVIEW_SYSTEM_PROMPT"] == "Focus on security only."


def test_build_agent_environment_omits_system_prompt_when_default() -> None:
    repo = replace(_repo_integration(), system_prompt="")
    env = build_agent_environment(
        review_id=str(_review_row().id),
        review=_review_row(),
        repo_integration=repo,
        llm_provider=_llm_provider(),
        infra=CodeReviewSettings(
            agent_callback_url="http://api:8000/api/v1/agent/review-events",
            agent_callback_secret="shared-secret",
        ),
    )

    assert "NEXO_COREVIEW_SYSTEM_PROMPT" not in env


def test_build_agent_environment_requires_callback_config() -> None:
    review = _review_row()
    infra = CodeReviewSettings(agent_callback_secret="")

    try:
        build_agent_environment(
            review_id=str(review.id),
            review=review,
            repo_integration=_repo_integration(),
            llm_provider=_llm_provider(),
            infra=infra,
        )
    except ValueError as exc:
        assert "AGENT_CALLBACK_SECRET" in str(exc)
    else:
        raise AssertionError("expected ValueError")
