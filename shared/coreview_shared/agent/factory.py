from coreview_shared.agent.models import (
    AgentRunConfig,
    OpenCodeRunConfig,
    ReviewAgentKind,
)
from coreview_shared.agent.opencode import OpenCodeAgent
from coreview_shared.agent.protocol import ReviewAgentAdapter


def build_review_agent(
    kind: ReviewAgentKind,
    config: AgentRunConfig,
) -> ReviewAgentAdapter:
    if kind is ReviewAgentKind.OPENCODE:
        if not isinstance(config, OpenCodeRunConfig):
            msg = "OpenCode agent requires OpenCodeRunConfig"
            raise TypeError(msg)
        return OpenCodeAgent(config=config)
    if kind is ReviewAgentKind.CURSOR_CLI:
        msg = "Review agent kind 'cursor-cli' is not implemented yet"
        raise NotImplementedError(msg)
    if kind is ReviewAgentKind.CLAUDE_CODE:
        msg = "Review agent kind 'claude-code' is not implemented yet"
        raise NotImplementedError(msg)
    if kind is ReviewAgentKind.OPENCLAUDE:
        msg = "Review agent kind 'openclaude' is not implemented yet"
        raise NotImplementedError(msg)
    msg = f"Unsupported review agent kind: {kind}"
    raise NotImplementedError(msg)
