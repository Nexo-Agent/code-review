from urllib.parse import quote

import httpx

from coreview_shared.git.gitlab import (
    DEFAULT_GITLAB_BASE_URL,
    normalize_gitlab_base_url,
    parse_repo_full_name,
)


class GitLabCIProvider:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_GITLAB_BASE_URL,
    ) -> None:
        self._token = token
        self._base_url = normalize_gitlab_base_url(base_url)

    def _api_base(self) -> str:
        return f"{self._base_url}/api/v4"

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["PRIVATE-TOKEN"] = self._token
        return headers

    def _encode_project(self, path_with_namespace: str) -> str:
        return quote(parse_repo_full_name(path_with_namespace), safe="")

    async def get_ci_summary(self, repo_full_name: str, head_sha: str) -> str:
        project = self._encode_project(repo_full_name)
        async with httpx.AsyncClient(timeout=30.0) as client:
            statuses_response = await client.get(
                f"{self._api_base()}/projects/{project}/repository/commits/{head_sha}/statuses",
                headers=self._headers(),
            )
            if statuses_response.status_code == 404:
                return "No CI checks found."
            statuses_response.raise_for_status()
            statuses = statuses_response.json()

        lines: list[str] = []
        if isinstance(statuses, list):
            for status in statuses:
                if not isinstance(status, dict):
                    continue
                name = status.get("name", "check")
                state = status.get("status", "unknown")
                lines.append(f"- {name}: {state}")

        if not lines:
            async with httpx.AsyncClient(timeout=30.0) as client:
                pipelines_response = await client.get(
                    f"{self._api_base()}/projects/{project}/pipelines",
                    headers=self._headers(),
                    params={"sha": head_sha},
                )
                if pipelines_response.status_code == 404:
                    return "No CI checks found."
                pipelines_response.raise_for_status()
                pipelines = pipelines_response.json()

            if isinstance(pipelines, list):
                for pipeline in pipelines:
                    if not isinstance(pipeline, dict):
                        continue
                    ref = pipeline.get("ref", "pipeline")
                    state = pipeline.get("status", "unknown")
                    lines.append(f"- pipeline/{ref}: {state}")

        if not lines:
            return "No CI checks found."
        return "\n".join(lines)
