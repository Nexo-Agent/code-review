from coreview_shared.agent.models import AgentRunConfig, ReviewRunResult
from coreview_shared.agent.protocol import ReviewAgentAdapter
from coreview_shared.review import PRContext
from coreview_shared.workspace.models import Workspace


class CursorCliAgent(ReviewAgentAdapter):
    def __init__(self, config: AgentRunConfig) -> None:
        self._config = config

    async def setup(self) -> None:
        return None

    async def run_review(
        self,
        workspace: Workspace,
        context: PRContext,
    ) -> ReviewRunResult:
        del workspace, context
        msg = "Cursor CLI review agent is not implemented yet"
        raise NotImplementedError(msg)

    async def teardown(self) -> None:
        return None
