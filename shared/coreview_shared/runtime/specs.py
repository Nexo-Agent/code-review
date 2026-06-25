from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

VolumeKind = Literal["bind", "configmap", "secret", "empty_dir"]


@dataclass(frozen=True, slots=True)
class VolumeMount:
    source: str
    target: str
    read_only: bool = False
    kind: VolumeKind = "bind"


@dataclass(frozen=True, slots=True)
class JobSpec:
    job_id: str
    image: str
    command: list[str]
    environment: dict[str, str]
    volumes: tuple[VolumeMount, ...]
    labels: dict[str, str]
    network: str | None = None
    extra_hosts: dict[str, str] | None = None
    stream_logs: bool = True
    mem_limit: str | None = None
    nano_cpus: int | None = None


@dataclass(frozen=True, slots=True)
class JobResult:
    exit_code: int
    log_tail: str = ""


@dataclass(frozen=True, slots=True)
class ReviewJobRequest:
    review_id: str
    environment: dict[str, str]
