"""Agent implementations and shared config builders for review execution."""

from coreview_shared.agent.factory import build_review_agent
from coreview_shared.agent.models import OpenCodeRunConfig, ReviewAgentKind
from coreview_shared.agent.opencode import OpenCodeAgent
from coreview_shared.agent.protocol import ReviewAgentAdapter

__all__ = [
    "ReviewAgentAdapter",
    "ReviewAgentKind",
    "OpenCodeRunConfig",
    "OpenCodeAgent",
    "build_review_agent",
]
