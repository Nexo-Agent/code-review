from app.config import AgentSettings

_REQUIRED_STRING_FIELDS = (
    "review_id",
    "repo_full_name",
    "head_sha",
    "github_token",
    "llm_provider_id",
    "llm_base_url",
    "llm_api_token",
    "llm_model",
    "callback_url",
    "callback_secret",
)


def require_review_env(settings: AgentSettings) -> None:
    """Fail fast when the job did not inject required execution env vars."""
    missing: list[str] = []
    for field in _REQUIRED_STRING_FIELDS:
        value = getattr(settings, field, "")
        if not str(value).strip():
            missing.append(f"NEXO_COREVIEW_{field.upper()}")

    if not settings.resolved_opencode_model:
        missing.append("NEXO_COREVIEW_OPENCODE_MODEL (or LLM provider + model)")

    if settings.pr_number <= 0:
        missing.append("NEXO_COREVIEW_PR_NUMBER")

    if missing:
        msg = f"Missing required review environment: {', '.join(missing)}"
        raise ValueError(msg)
