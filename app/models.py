from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExperimentRow:
    user_id: str
    group: str
    segment: str
    pre_metric: float
    outcome_metric: float
    guardrail_contact_rate: float
    guardrail_latency_ms: float


@dataclass(frozen=True)
class GroupStats:
    users: int
    mean: float
    variance: float
