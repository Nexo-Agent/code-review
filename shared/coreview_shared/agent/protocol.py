from typing import Protocol

from coreview_shared.agent.models import ReviewRunResult
from coreview_shared.review import PRContext
from coreview_shared.workspace.models import Workspace


class ReviewAgentAdapter(Protocol):
    async def setup(self) -> None: ...

    async def run_review(
        self,
        workspace: Workspace,
        context: PRContext,
    ) -> ReviewRunResult: ...

    async def teardown(self) -> None: ...
