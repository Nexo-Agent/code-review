import httpx


class GitHubCIProvider:
    API_BASE = "https://api.github.com"

    def __init__(self, token: str) -> None:
        self._token = token

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def get_ci_summary(self, repo_full_name: str, head_sha: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.API_BASE}/repos/{repo_full_name}/commits/{head_sha}/check-runs",
                headers=self._headers(),
                params={"per_page": 100},
            )
            if response.status_code == 404:
                return "No CI checks found."
            response.raise_for_status()
            runs = response.json().get("check_runs", [])

        if not runs:
            return "No CI checks found."

        lines: list[str] = []
        for run in runs:
            status = run.get("status", "unknown")
            conclusion = run.get("conclusion") or "pending"
            name = run.get("name", "check")
            lines.append(f"- {name}: {status}/{conclusion}")
        return "\n".join(lines)
