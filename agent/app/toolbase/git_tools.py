from dataclasses import asdict
from typing import Any

from coreview_shared.git.models import InlineComment

from app.toolbase.context import ToolContext, providers_for_repo


def _metadata_dict(metadata: Any) -> dict[str, Any]:
    return asdict(metadata)


async def fetch_pr_context(
    ctx: ToolContext,
    repo_full_name: str,
    pr_number: int,
    head_sha: str,
) -> dict[str, Any]:
    providers = await providers_for_repo(ctx, repo_full_name)
    pr_context = await providers.git.fetch_pr_context(
        repo_full_name, pr_number, head_sha
    )
    return {
        "metadata": _metadata_dict(pr_context.metadata),
        "diff": pr_context.diff,
        "ci_summary": pr_context.ci_summary,
    }


async def get_pr_metadata(
    ctx: ToolContext,
    repo_full_name: str,
    pr_number: int,
) -> dict[str, Any]:
    providers = await providers_for_repo(ctx, repo_full_name)
    metadata = await providers.git.get_pr_metadata(repo_full_name, pr_number)
    return _metadata_dict(metadata)


async def get_pr_diff(
    ctx: ToolContext,
    repo_full_name: str,
    pr_number: int,
) -> dict[str, str]:
    providers = await providers_for_repo(ctx, repo_full_name)
    diff = await providers.git.get_pr_diff(repo_full_name, pr_number)
    return {"diff": diff}


async def post_review_comment(
    ctx: ToolContext,
    repo_full_name: str,
    pr_number: int,
    body: str,
) -> dict[str, str]:
    providers = await providers_for_repo(ctx, repo_full_name)
    await providers.git.post_review_comment(repo_full_name, pr_number, body)
    return {"status": "posted"}


async def post_inline_comments(
    ctx: ToolContext,
    repo_full_name: str,
    pr_number: int,
    commit_id: str,
    comments: list[dict[str, Any]],
    body: str = "",
) -> dict[str, str]:
    providers = await providers_for_repo(ctx, repo_full_name)
    inline = [
        InlineComment(
            path=c["path"],
            line=int(c["line"]),
            body=c["body"],
            side=c.get("side", "RIGHT"),
        )
        for c in comments
    ]
    result = await providers.git.post_inline_comments(
        repo_full_name,
        pr_number,
        commit_id,
        inline,
        body=body,
    )
    return {
        "status": "posted",
        "posted": str(len(result.posted)),
        "skipped": str(len(result.skipped)),
    }
