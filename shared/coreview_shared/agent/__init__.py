"""Agent implementations and shared config builders for review execution."""

from coreview_shared.agent.opencode import OpenCodeAgent
from coreview_shared.agent.protocol import AgentProvider

__all__ = ["AgentProvider", "OpenCodeAgent"]
