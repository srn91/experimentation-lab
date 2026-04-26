from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExperimentRow:
    user_id: str
    group: str
    pre_metric: float
    outcome_metric: float


@dataclass(frozen=True)
class GroupStats:
    users: int
    mean: float
    variance: float

