from dataclasses import dataclass, field

from coreview_shared.ci.protocol import CIProvider
from coreview_shared.git.protocol import GitProvider
from coreview_shared.runtime.protocol import RuntimeProvider


@dataclass(slots=True)
class ProviderBundle:
    git: GitProvider
    ci: CIProvider
    runtime: RuntimeProvider | None = None
    extra: dict[str, object] = field(default_factory=dict)
