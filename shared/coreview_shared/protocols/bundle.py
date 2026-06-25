from dataclasses import dataclass, field

from coreview_shared.protocols.ci import CIProvider
from coreview_shared.protocols.git import GitProvider
from coreview_shared.protocols.runtime import RuntimeProvider


@dataclass(slots=True)
class ProviderBundle:
    git: GitProvider
    ci: CIProvider
    runtime: RuntimeProvider | None = None
    extra: dict[str, object] = field(default_factory=dict)
