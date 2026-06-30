from coreview_shared.agent.models import AgentRunConfig
from coreview_shared.agent.protocol import ReviewAgentAdapter
from coreview_shared.review import PRContext, ReviewFinding
from coreview_shared.workspace.models import Workspace


class ClaudeCodeAgent(ReviewAgentAdapter):
    def __init__(self, config: AgentRunConfig) -> None:
        self._config = config

    async def setup(self) -> None:
        return None

    async def run_review(
        self,
        workspace: Workspace,
        context: PRContext,
    ) -> list[ReviewFinding]:
        del workspace, context
        msg = "Claude Code review agent is not implemented yet"
        raise NotImplementedError(msg)

    async def teardown(self) -> None:
        return None
