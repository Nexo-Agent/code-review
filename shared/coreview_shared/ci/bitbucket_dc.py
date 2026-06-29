import httpx

from coreview_shared.git.bitbucket_dc import (
    normalize_base_url,
    parse_repo_full_name,
)


class BitbucketDataCenterCIProvider:
    def __init__(self, token: str, *, base_url: str) -> None:
        self._token = token
        self._base_url = normalize_base_url(base_url)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _api_base(self) -> str:
        return f"{self._base_url}/rest/api/latest"

    async def get_ci_summary(self, repo_full_name: str, head_sha: str) -> str:
        project_key, repo_slug = parse_repo_full_name(repo_full_name)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._api_base()}/projects/{project_key}/repos/{repo_slug}"
                f"/commits/{head_sha}/builds",
                headers=self._headers(),
            )
            if response.status_code == 404:
                return "No CI checks found."
            response.raise_for_status()
            payload = response.json()

        lines: list[str] = []
        values = payload.get("values", []) if isinstance(payload, dict) else []
        if isinstance(values, list):
            for build in values:
                if not isinstance(build, dict):
                    continue
                name = build.get("name", "build")
                state = build.get("state", "unknown")
                lines.append(f"- {name}: {state}")

        if not lines:
            return "No CI checks found."
        return "\n".join(lines)
