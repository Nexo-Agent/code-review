import json
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.config import CodeReviewSettings
from app.repositories.llm_providers import LlmProviderRow
from app.repositories.organizations import DEFAULT_ORG_ID
from app.repositories.repo_integrations import RepoIntegrationRow
from app.repositories.reviews import ReviewRow
from app.repositories.teams import DEFAULT_TEAM_ID
from app.services.review_job_prepare import build_agent_environment
from tests.conftest import make_review_row


def _review_row() -> ReviewRow:
    return make_review_row(
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        pr_title="Fix login bug",
        delivery_id="del-1",
    )


def _repo_integration() -> RepoIntegrationRow:
    now = datetime.now(tz=UTC)
    return RepoIntegrationRow(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        team_id=DEFAULT_TEAM_ID,
        name="org/repo",
        git_provider="github",
        repo_full_name="org/repo",
        llm_provider_id=None,
        github_webhook_secret="secret",
        github_token="ghp_test",
        system_prompt="Focus on security only.",
        enabled=True,
        ado_organization="",
        ado_project="",
        ado_pat="",
        ado_webhook_username="",
        ado_webhook_password="",
        gitlab_base_url="",
        gitlab_token="",
        gitlab_webhook_secret="",
        bitbucket_token="",
        bitbucket_webhook_secret="",
        bitbucket_dc_base_url="",
        bitbucket_dc_token="",
        bitbucket_dc_webhook_username="",
        bitbucket_dc_webhook_password="",
        created_at=now,
        updated_at=now,
    )


def _llm_provider() -> LlmProviderRow:
    now = datetime.now(tz=UTC)
    return LlmProviderRow(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        organization_id=DEFAULT_ORG_ID,
        name="default",
        provider_id="openai-compat",
        base_url="https://api.example.com/v1",
        api_token="sk-test",
        model="gpt-4o",
        opencode_model="",
        is_default=True,
        enabled=True,
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

    assert env["COGITO_REVIEW_REPO_FULL_NAME"] == "org/repo"
    assert env["COGITO_REVIEW_PR_NUMBER"] == "42"
    assert env["COGITO_REVIEW_HEAD_SHA"] == "abc123"
    assert env["COGITO_REVIEW_GITHUB_TOKEN"] == "ghp_test"
    assert env["COGITO_REVIEW_LLM_API_TOKEN"] == "sk-test"
    assert env["COGITO_REVIEW_OPENCODE_MODEL"] == "openai-compat/gpt-4o"
    assert env["COGITO_REVIEW_REVIEW_TIMEOUT_SECONDS"] == "900"
    assert env["COGITO_REVIEW_REVIEW_ID"] == str(review.id)
    assert (
        env["COGITO_REVIEW_CALLBACK_URL"]
        == "http://api:8000/api/v1/agent/review-events"
    )
    assert env["COGITO_REVIEW_CALLBACK_SECRET"] == "shared-secret"
    assert "DATABASE_URL" not in env

    metadata = json.loads(env["COGITO_REVIEW_CALLBACK_METADATA"])
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

    assert env["COGITO_REVIEW_GIT_PROVIDER"] == "azure-devops"
    assert env["COGITO_REVIEW_ADO_ORGANIZATION"] == "fabrikam"
    assert env["COGITO_REVIEW_ADO_PROJECT"] == "MyProject"
    assert env["COGITO_REVIEW_ADO_PAT"] == "ado-pat"


def test_build_agent_environment_includes_gitlab_credentials() -> None:
    review = _review_row()
    repo_integration = replace(
        _repo_integration(),
        git_provider="gitlab",
        repo_full_name="acme/backend",
        gitlab_base_url="https://gitlab.example.com",
        gitlab_token="glpat-test",
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

    assert env["COGITO_REVIEW_GIT_PROVIDER"] == "gitlab"
    assert env["COGITO_REVIEW_GITLAB_BASE_URL"] == "https://gitlab.example.com"
    assert env["COGITO_REVIEW_GITLAB_TOKEN"] == "glpat-test"


def test_build_agent_environment_includes_bitbucket_credentials() -> None:
    review = _review_row()
    repo_integration = replace(
        _repo_integration(),
        git_provider="bitbucket",
        repo_full_name="acme/backend",
        bitbucket_token="bb-token",
        bitbucket_webhook_secret="hook-secret",
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

    assert env["COGITO_REVIEW_GIT_PROVIDER"] == "bitbucket"
    assert env["COGITO_REVIEW_BITBUCKET_TOKEN"] == "bb-token"


def test_build_agent_environment_includes_bitbucket_dc_credentials() -> None:
    review = _review_row()
    repo_integration = replace(
        _repo_integration(),
        git_provider="bitbucket-dc",
        repo_full_name="ACME/backend",
        bitbucket_dc_base_url="https://bitbucket.example.com",
        bitbucket_dc_token="dc-token",
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

    assert env["COGITO_REVIEW_GIT_PROVIDER"] == "bitbucket-dc"
    assert env["COGITO_REVIEW_BITBUCKET_DC_BASE_URL"] == "https://bitbucket.example.com"
    assert env["COGITO_REVIEW_BITBUCKET_DC_TOKEN"] == "dc-token"


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

    assert env["COGITO_REVIEW_SYSTEM_PROMPT"] == "Focus on security only."


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

    assert "COGITO_REVIEW_SYSTEM_PROMPT" not in env


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
