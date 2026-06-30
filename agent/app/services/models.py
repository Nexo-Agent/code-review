from __future__ import annotations

from dataclasses import dataclass, field

from coreview_shared.agent.models import AgentRunConfig, ReviewAgentKind
from coreview_shared.git.models import InlineComment, PreparedReview
from coreview_shared.providers import ProviderBundle
from coreview_shared.review import ReviewFinding
from coreview_shared.schemas.review_callback import ReviewCallbackRequest

from app.config import AgentSettings


@dataclass(slots=True)
class ReviewRunContext:
    review_id: str
    settings: AgentSettings
    providers: ProviderBundle
    callback_request: ReviewCallbackRequest
    agent_kind: ReviewAgentKind
    agent_config: AgentRunConfig
    prepared_review: PreparedReview | None = None


@dataclass(frozen=True, slots=True)
class ReviewPublishResult:
    findings: tuple[ReviewFinding, ...]
    posted_inline_comments: tuple[InlineComment, ...] = field(default_factory=tuple)
    inline_comments_posted: int = 0
    inline_comments_skipped: int = 0
    summary_comment_posted: bool = False
