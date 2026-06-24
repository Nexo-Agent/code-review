from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class IntegrationSettingsRow:
    git_provider: str
    github_repo_full_name: str
    github_webhook_secret: str
    github_token: str
    llm_provider_id: str
    llm_base_url: str
    llm_api_token: str
    llm_model: str
    opencode_model: str
    updated_at: datetime

    @property
    def resolved_opencode_model(self) -> str:
        if self.opencode_model:
            return self.opencode_model
        return f"{self.llm_provider_id}/{self.llm_model}"

    def accepts_repo(self, repo_full_name: str) -> bool:
        if not self.github_repo_full_name.strip():
            return True
        return repo_full_name.strip() == self.github_repo_full_name.strip()


class IntegrationSettingsRepository:
    _SELECT = """
        SELECT git_provider, github_repo_full_name, github_webhook_secret,
               github_token, llm_provider_id, llm_base_url, llm_api_token,
               llm_model, opencode_model, updated_at
        FROM integration_settings WHERE id = 1
    """

    def __init__(self, conn) -> None:
        self._conn = conn

    async def get(self) -> IntegrationSettingsRow:
        row = await self._conn.fetchrow(self._SELECT)
        if row is None:
            msg = "integration_settings row missing"
            raise RuntimeError(msg)
        return _to_row(row)

    async def update(
        self,
        *,
        git_provider: str | None = None,
        github_repo_full_name: str | None = None,
        github_webhook_secret: str | None = None,
        github_token: str | None = None,
        llm_provider_id: str | None = None,
        llm_base_url: str | None = None,
        llm_api_token: str | None = None,
        llm_model: str | None = None,
        opencode_model: str | None = None,
        clear_github_token: bool = False,
        clear_llm_api_token: bool = False,
        clear_webhook_secret: bool = False,
    ) -> IntegrationSettingsRow:
        current = await self.get()
        row = await self._conn.fetchrow(
            """
            UPDATE integration_settings
            SET git_provider = $1,
                github_repo_full_name = $2,
                github_webhook_secret = $3,
                github_token = $4,
                llm_provider_id = $5,
                llm_base_url = $6,
                llm_api_token = $7,
                llm_model = $8,
                opencode_model = $9,
                updated_at = now()
            WHERE id = 1
            RETURNING git_provider, github_repo_full_name, github_webhook_secret,
                      github_token, llm_provider_id, llm_base_url, llm_api_token,
                      llm_model, opencode_model, updated_at
            """,
            git_provider if git_provider is not None else current.git_provider,
            github_repo_full_name
            if github_repo_full_name is not None
            else current.github_repo_full_name,
            ""
            if clear_webhook_secret
            else github_webhook_secret
            if github_webhook_secret is not None
            else current.github_webhook_secret,
            ""
            if clear_github_token
            else github_token
            if github_token is not None
            else current.github_token,
            llm_provider_id
            if llm_provider_id is not None
            else current.llm_provider_id,
            llm_base_url if llm_base_url is not None else current.llm_base_url,
            ""
            if clear_llm_api_token
            else llm_api_token
            if llm_api_token is not None
            else current.llm_api_token,
            llm_model if llm_model is not None else current.llm_model,
            opencode_model
            if opencode_model is not None
            else current.opencode_model,
        )
        if row is None:
            msg = "Failed to update integration settings"
            raise RuntimeError(msg)
        return _to_row(row)


def _to_row(row) -> IntegrationSettingsRow:
    return IntegrationSettingsRow(
        git_provider=row["git_provider"],
        github_repo_full_name=row["github_repo_full_name"],
        github_webhook_secret=row["github_webhook_secret"],
        github_token=row["github_token"],
        llm_provider_id=row["llm_provider_id"],
        llm_base_url=row["llm_base_url"],
        llm_api_token=row["llm_api_token"],
        llm_model=row["llm_model"],
        opencode_model=row["opencode_model"],
        updated_at=row["updated_at"],
    )
