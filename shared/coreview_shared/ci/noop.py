class NoOpCIProvider:
    async def get_ci_summary(self, repo_full_name: str, head_sha: str) -> str:
        del repo_full_name, head_sha
        return "No CI checks found."
