from __future__ import annotations

from coreview_shared.runtime.specs import JobResult, JobSpec


class K8sJobExecutor:
    async def run(self, spec: JobSpec) -> JobResult:
        raise NotImplementedError("K8s runtime not implemented yet")

    async def cleanup_stale(self, labels: dict[str, str]) -> None:
        raise NotImplementedError("K8s runtime not implemented yet")
