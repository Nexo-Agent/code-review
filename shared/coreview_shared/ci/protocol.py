from typing import Protocol


class CIProvider(Protocol):
    async def get_ci_summary(self, repo_full_name: str, head_sha: str) -> str: ...
