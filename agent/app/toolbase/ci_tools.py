from app.toolbase.context import ToolContext, providers_for_repo


async def get_ci_summary(
    ctx: ToolContext,
    repo_full_name: str,
    head_sha: str,
) -> dict[str, str]:
    providers = await providers_for_repo(ctx, repo_full_name)
    summary = await providers.ci.get_ci_summary(repo_full_name, head_sha)
    return {"summary": summary}
