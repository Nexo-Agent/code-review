import httpx

from coreview_shared.git.bitbucket_cloud import (
    API_BASE,
    parse_repo_full_name,
)


class BitbucketCloudCIProvider:
    def __init__(self, token: str) -> None:
        self._token = token

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def get_ci_summary(self, repo_full_name: str, head_sha: str) -> str:
        workspace, repo_slug = parse_repo_full_name(repo_full_name)
        async with httpx.AsyncClient(timeout=30.0) as client:
            statuses_response = await client.get(
                f"{API_BASE}/repositories/{workspace}/{repo_slug}"
                f"/commit/{head_sha}/statuses",
                headers=self._headers(),
            )
            if statuses_response.status_code == 404:
                return "No CI checks found."
            statuses_response.raise_for_status()
            payload = statuses_response.json()

        lines: list[str] = []
        values = payload.get("values", []) if isinstance(payload, dict) else []
        if isinstance(values, list):
            for status in values:
                if not isinstance(status, dict):
                    continue
                name = status.get("name", "check")
                state = status.get("state", "unknown")
                lines.append(f"- {name}: {state}")

        if not lines:
            async with httpx.AsyncClient(timeout=30.0) as client:
                pipelines_response = await client.get(
                    f"{API_BASE}/repositories/{workspace}/{repo_slug}/pipelines",
                    headers=self._headers(),
                    params={"target.commit.hash": head_sha},
                )
                if pipelines_response.status_code == 404:
                    return "No CI checks found."
                pipelines_response.raise_for_status()
                pipelines_payload = pipelines_response.json()

            pipeline_values = (
                pipelines_payload.get("values", [])
                if isinstance(pipelines_payload, dict)
                else []
            )
            if isinstance(pipeline_values, list):
                for pipeline in pipeline_values:
                    if not isinstance(pipeline, dict):
                        continue
                    state_obj = pipeline.get("state", {})
                    state = (
                        state_obj.get("name", "unknown")
                        if isinstance(state_obj, dict)
                        else "unknown"
                    )
                    build_number = pipeline.get("build_number", "pipeline")
                    lines.append(f"- pipeline/{build_number}: {state}")

        if not lines:
            return "No CI checks found."
        return "\n".join(lines)
