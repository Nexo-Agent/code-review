import hashlib
import hmac

import httpx

from app.providers.protocols import PRContext, PRMetadata


class GitHubProvider:
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

    def verify_webhook_signature(
        self, payload: bytes, signature: str | None, secret: str
    ) -> bool:
        if not secret:
            return False
        if not signature or not signature.startswith("sha256="):
            return False
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature.removeprefix("sha256="), expected)

    async def fetch_pr_context(
        self, repo_full_name: str, pr_number: int, head_sha: str
    ) -> PRContext:
        metadata = await self.get_pr_metadata(repo_full_name, pr_number)
        diff = await self.get_pr_diff(repo_full_name, pr_number)
        return PRContext(metadata=metadata, diff=diff)

    async def get_pr_metadata(
        self, repo_full_name: str, pr_number: int
    ) -> PRMetadata:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.API_BASE}/repos/{repo_full_name}/pulls/{pr_number}",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
        return PRMetadata(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            title=data["title"],
            author=data["user"]["login"],
            head_sha=data["head"]["sha"],
            base_sha=data["base"]["sha"],
            head_ref=data["head"]["ref"],
            base_ref=data["base"]["ref"],
            html_url=data["html_url"],
        )

    async def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
        headers = self._headers()
        headers["Accept"] = "application/vnd.github.diff"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{self.API_BASE}/repos/{repo_full_name}/pulls/{pr_number}",
                headers=headers,
            )
            response.raise_for_status()
            return response.text

    async def post_review_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        body: str,
    ) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.API_BASE}/repos/{repo_full_name}/issues/{pr_number}/comments",
                headers=self._headers(),
                json={"body": body},
            )
            response.raise_for_status()
