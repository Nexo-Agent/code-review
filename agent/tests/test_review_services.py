from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from coreview_shared.agent.models import OpenCodeRunConfig, ReviewAgentKind
from coreview_shared.git.models import (
    InlineComment,
    InlineCommentsResult,
    PreparedReview,
    RemoteRepoAccess,
    ReviewCommentArtifact,
)
from coreview_shared.providers import ProviderBundle
from coreview_shared.review import PRContext, PRMetadata, ReviewFinding
from coreview_shared.schemas.review_callback import ReviewCallbackRequest
from coreview_shared.workspace.models import PreparedWorkspace, Workspace, WorkspaceSpec

from app.config import AgentSettings
from app.services.models import ReviewRunContext
from app.services.review_context import build_review_context, require_review_env
from app.services.review_reporter import (
    ReviewReporter,
    _format_summary_comment,
    _split_findings,
)
from app.services.review_runner import execute_review_logic


def _settings(**overrides: object) -> AgentSettings:
    base = {
        "review_id": "550e8400-e29b-41d4-a716-446655440000",
        "repo_full_name": "org/repo",
        "pr_number": 7,
        "head_sha": "deadbeef",
        "github_token": "ghp_test",
        "llm_provider_id": "openai-compat",
        "llm_base_url": "https://api.example.com/v1",
        "llm_api_token": "sk-test",
        "llm_model": "gpt-4o",
        "opencode_model": "openai-compat/gpt-4o",
        "callback_url": "http://localhost:8000/api/v1/agent/review-events",
        "callback_secret": "dev-secret",
    }
    base.update(overrides)
    return AgentSettings(**base)


def _prepared_review() -> PreparedReview:
    spec = WorkspaceSpec(
        review_id="r1",
        repo_full_name="org/repo",
        pr_number=7,
        head_sha="deadbeef",
    )
    workspace = Workspace(path=Path("/tmp/worktree"), spec=spec)
    prepared_workspace = PreparedWorkspace(
        repo_base=Path("/tmp/repo"),
        mirror_path=Path("/tmp/repo/mirror.git"),
        worktree_path=Path("/tmp/worktree"),
        workspace=workspace,
    )
    context = PRContext(
        metadata=PRMetadata(
            repo_full_name="org/repo",
            pr_number=7,
            title="Test PR",
            author="dev",
            head_sha="deadbeef",
            base_sha="cafebabe",
            head_ref="feature",
            base_ref="main",
            html_url="https://example.com/pr/7",
        ),
        diff="diff",
    )
    return PreparedReview(
        context=context,
        workspace=prepared_workspace,
        remote_access=RemoteRepoAccess(clone_url="https://example.com/repo.git"),
    )


def _run_context() -> ReviewRunContext:
    providers = ProviderBundle(git=AsyncMock(), ci=AsyncMock())
    prepared_review = _prepared_review()
    return ReviewRunContext(
        review_id="r1",
        settings=_settings(),
        providers=providers,
        callback_request=ReviewCallbackRequest(
            git_provider="github",
            repo_full_name="org/repo",
            pr_number=7,
            head_sha="deadbeef",
        ),
        agent_kind=ReviewAgentKind.OPENCODE,
        agent_config=OpenCodeRunConfig(
            kind=ReviewAgentKind.OPENCODE,
            review_id="r1",
            agent="code-reviewer",
            model="openai-compat/gpt-4o",
            timeout_seconds=60,
            log_level="INFO",
            llm_provider_id="openai-compat",
            llm_base_url="https://api.example.com/v1",
            llm_api_token="sk-test",
            llm_model="gpt-4o",
        ),
        prepared_review=prepared_review,
    )


def test_require_review_env_accepts_full_settings() -> None:
    require_review_env(_settings())


def test_require_review_env_raises_when_missing_token() -> None:
    with pytest.raises(ValueError, match="COGITO_REVIEW_GITHUB_TOKEN"):
        require_review_env(_settings(github_token=""))


def test_require_review_env_accepts_gitlab_settings() -> None:
    require_review_env(
        _settings(
            git_provider="gitlab",
            github_token="",
            gitlab_token="glpat-test",
        )
    )


def test_require_review_env_raises_when_missing_gitlab_token() -> None:
    with pytest.raises(ValueError, match="COGITO_REVIEW_GITLAB_TOKEN"):
        require_review_env(
            _settings(
                git_provider="gitlab",
                github_token="",
                gitlab_token="",
            )
        )


def test_require_review_env_accepts_bitbucket_settings() -> None:
    require_review_env(
        _settings(
            git_provider="bitbucket",
            github_token="",
            bitbucket_token="bb-token",
        )
    )


def test_require_review_env_raises_when_missing_bitbucket_token() -> None:
    with pytest.raises(ValueError, match="COGITO_REVIEW_BITBUCKET_TOKEN"):
        require_review_env(
            _settings(
                git_provider="bitbucket",
                github_token="",
                bitbucket_token="",
            )
        )


def test_require_review_env_accepts_bitbucket_dc_settings() -> None:
    require_review_env(
        _settings(
            git_provider="bitbucket-dc",
            github_token="",
            bitbucket_dc_base_url="https://bitbucket.example.com",
            bitbucket_dc_token="dc-token",
        )
    )


def test_require_review_env_raises_when_missing_bitbucket_dc_token() -> None:
    with pytest.raises(ValueError, match="COGITO_REVIEW_BITBUCKET_DC_TOKEN"):
        require_review_env(
            _settings(
                git_provider="bitbucket-dc",
                github_token="",
                bitbucket_dc_base_url="https://bitbucket.example.com",
                bitbucket_dc_token="",
            )
        )


def test_require_review_env_raises_when_missing_callback() -> None:
    with pytest.raises(ValueError, match="COGITO_REVIEW_CALLBACK_URL"):
        require_review_env(_settings(callback_url=""))


def test_agent_kind_defaults_to_opencode() -> None:
    assert _settings().agent_kind is ReviewAgentKind.OPENCODE


@pytest.mark.asyncio
async def test_build_review_context_assembles_prepared_review() -> None:
    settings = _settings(review_id="r1")
    prepared_review = _prepared_review()
    providers = ProviderBundle(git=AsyncMock(), ci=AsyncMock())
    providers.ci.get_ci_summary.return_value = "CI ok"
    providers.git.prepare_review.return_value = prepared_review

    with patch(
        "app.services.review_context.build_providers_from_env",
        return_value=providers,
    ):
        context = await build_review_context("r1", settings)

    assert context.prepared_review is not None
    assert context.prepared_review.context.ci_summary == "CI ok"
    assert context.callback_request.pr_title == "Test PR"
    assert context.agent_kind is ReviewAgentKind.OPENCODE


@pytest.mark.asyncio
async def test_review_reporter_posts_comments_and_tracks_stats() -> None:
    context = _run_context()
    context.providers.git.publish_inline_comments.return_value = InlineCommentsResult(
        posted=(
            ReviewCommentArtifact(
                comment_kind="inline",
                remote_comment_id="101",
                path="a.py",
                line=5,
                body="one",
                finding_index=0,
            ),
        ),
        skipped=(InlineComment(path="b.py", line=9, body="two"),),
    )
    context.providers.git.publish_summary_comment.return_value = ReviewCommentArtifact(
        comment_kind="summary",
        remote_comment_id="201",
        body="summary",
    )
    reporter = ReviewReporter()
    findings = [
        ReviewFinding(
            severity="warning",
            title="Bug",
            body="details",
            file_path="a.py",
            line_start=5,
        ),
        ReviewFinding(
            severity="warning",
            title="Moved",
            body="details",
            file_path="b.py",
            line_start=9,
        ),
    ]

    result = await reporter.post_comments(context, findings)

    assert result.inline_comments_posted == 1
    assert result.inline_comments_skipped == 1
    assert result.summary_comment_posted is True
    assert len(result.posted_comment_artifacts) == 2
    context.providers.git.publish_summary_comment.assert_awaited_once()


def test_split_findings_adds_feedback_footer_to_inline_comment() -> None:
    inline, summary_only = _split_findings(
        [
            ReviewFinding(
                severity="warning",
                title="Bug",
                body="details",
                file_path="a.py",
                line_start=5,
            )
        ]
    )

    assert len(inline) == 1
    assert summary_only == []
    assert "Reply with one of:" in inline[0].body
    assert "`Helpful`" in inline[0].body


def test_format_summary_comment_adds_feedback_footer() -> None:
    body = _format_summary_comment([], "org/repo", 7)

    assert "No issues found. LGTM!" in body
    assert "Reply with one of:" in body
    assert "`Applied`" in body


@pytest.mark.asyncio
async def test_review_reporter_send_callback_posts_with_signature() -> None:
    context = _run_context()
    reporter = ReviewReporter()

    mock_response = MagicMock(status_code=204)
    mock_http = AsyncMock()
    mock_http.post.return_value = mock_response
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None

    with patch(
        "app.services.review_reporter.httpx.AsyncClient",
        return_value=mock_http,
    ):
        await reporter.send_callback("review.started", context)

    call_kwargs = mock_http.post.call_args.kwargs
    assert call_kwargs["content"]
    assert call_kwargs["headers"]["X-Review-Signature-256"].startswith("sha256=")


@pytest.mark.asyncio
async def test_review_reporter_retries_on_5xx() -> None:
    context = _run_context()
    reporter = ReviewReporter()

    fail_response = MagicMock(status_code=503, text="unavailable")
    ok_response = MagicMock(status_code=204)
    mock_http = AsyncMock()
    mock_http.post.side_effect = [fail_response, ok_response]
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None

    with (
        patch("app.services.review_reporter.httpx.AsyncClient", return_value=mock_http),
        patch("app.services.review_reporter.asyncio.sleep", new=AsyncMock()),
    ):
        await reporter.send_callback(
            "review.failed",
            context,
            error=RuntimeError("boom"),
        )

    assert mock_http.post.await_count == 2


@pytest.mark.asyncio
async def test_execute_review_logic_success_path() -> None:
    context = _run_context()
    agent = AsyncMock()
    findings = [ReviewFinding(severity="info", title="Note", body="general")]

    with (
        patch("app.services.review_runner.clear_agent_settings_cache"),
        patch(
            "app.services.review_runner.get_agent_settings",
            return_value=_settings(),
        ),
        patch(
            "app.services.review_runner.build_review_context",
            new=AsyncMock(return_value=context),
        ),
        patch("app.services.review_runner.build_review_agent", return_value=agent),
        patch("app.services.review_runner.cleanup_review_context", new=AsyncMock()),
        patch("app.services.review_runner.ReviewReporter") as reporter_cls,
    ):
        reporter = AsyncMock()
        reporter.post_comments.return_value = MagicMock(
            summary_comment_posted=True,
            inline_comments_posted=0,
            inline_comments_skipped=0,
        )
        reporter_cls.return_value = reporter
        agent.run_review.return_value = findings

        await execute_review_logic("r1")

    reporter.send_callback.assert_any_await("review.started", context)
    reporter.post_comments.assert_awaited_once_with(context, findings)
    reporter.send_callback.assert_any_await(
        "review.completed",
        context,
        findings=findings,
        publish_result=reporter.post_comments.return_value,
    )
    agent.setup.assert_awaited_once()
    agent.teardown.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_review_logic_failure_sends_failed_callback() -> None:
    context = _run_context()
    agent = AsyncMock()
    agent.run_review.side_effect = RuntimeError("boom")

    with (
        patch("app.services.review_runner.clear_agent_settings_cache"),
        patch(
            "app.services.review_runner.get_agent_settings",
            return_value=_settings(),
        ),
        patch(
            "app.services.review_runner.build_review_context",
            new=AsyncMock(return_value=context),
        ),
        patch("app.services.review_runner.build_review_agent", return_value=agent),
        patch("app.services.review_runner.cleanup_review_context", new=AsyncMock()),
        patch("app.services.review_runner.ReviewReporter") as reporter_cls,
    ):
        reporter = AsyncMock()
        reporter_cls.return_value = reporter

        with pytest.raises(RuntimeError, match="boom"):
            await execute_review_logic("r1")

    reporter.send_callback.assert_any_await("review.started", context)
    reporter.send_callback.assert_any_await(
        "review.failed",
        context,
        error=agent.run_review.side_effect,
    )
    agent.teardown.assert_awaited_once()
