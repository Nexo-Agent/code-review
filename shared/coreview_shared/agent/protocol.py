from typing import Protocol

from coreview_shared.review import PRContext, ReviewFinding
from coreview_shared.workspace.models import Workspace


class AgentProvider(Protocol):
    async def run_review(
        self,
        workspace: Workspace,
        context: PRContext,
    ) -> list[ReviewFinding]: ...
