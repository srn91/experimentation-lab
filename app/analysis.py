from __future__ import annotations

import json
import math
from pathlib import Path

from app.models import ExperimentRow, GroupStats


def _mean(values: list[float]) -> float:
    if not values:
        raise ValueError("expected at least one value")
    return sum(values) / len(values)


def _variance(values: list[float], mean: float) -> float:
    if len(values) < 2:
        raise ValueError("expected at least two values for variance")
    return sum((value - mean) ** 2 for value in values) / (len(values) - 1)


def _group_stats(rows: list[ExperimentRow], metric_name: str) -> dict[str, GroupStats]:
    grouped: dict[str, list[float]] = {"control": [], "treatment": []}
    for row in rows:
        grouped[row.group].append(getattr(row, metric_name))

    stats: dict[str, GroupStats] = {}
    for group_name, values in grouped.items():
        mean = _mean(values)
        variance = _variance(values, mean)
        stats[group_name] = GroupStats(users=len(values), mean=mean, variance=variance)
    return stats


def _z_score(control: GroupStats, treatment: GroupStats) -> float:
    difference = treatment.mean - control.mean
    standard_error = math.sqrt(
        (control.variance / control.users) + (treatment.variance / treatment.users)
    )
    if standard_error == 0:
        raise ValueError("standard error is zero; cannot compute z-score")
    return difference / standard_error


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _two_sided_p_value(z_score: float) -> float:
    return 2.0 * (1.0 - _normal_cdf(abs(z_score)))


def _cuped_theta(rows: list[ExperimentRow]) -> float:
    if len(rows) < 2:
        raise ValueError("expected at least two rows for CUPED")
    pre_values = [row.pre_metric for row in rows]
    outcome_values = [row.outcome_metric for row in rows]
    pre_mean = _mean(pre_values)
    outcome_mean = _mean(outcome_values)
    covariance = sum(
        (pre_value - pre_mean) * (outcome_value - outcome_mean)
        for pre_value, outcome_value in zip(pre_values, outcome_values, strict=True)
    ) / (len(rows) - 1)
    pre_variance = _variance(pre_values, pre_mean)
    if pre_variance == 0:
        raise ValueError("pre-period variance is zero; CUPED is undefined")
    return covariance / pre_variance


def _apply_cuped(rows: list[ExperimentRow]) -> list[ExperimentRow]:
    theta = _cuped_theta(rows)
    pre_mean = _mean([row.pre_metric for row in rows])
    adjusted_rows: list[ExperimentRow] = []
    for row in rows:
        adjusted_rows.append(
            ExperimentRow(
                user_id=row.user_id,
                group=row.group,
                pre_metric=row.pre_metric,
                outcome_metric=row.outcome_metric - theta * (row.pre_metric - pre_mean),
            )
        )
    return adjusted_rows


def _sequential_snapshots(rows: list[ExperimentRow]) -> list[dict[str, float | int | str]]:
    checkpoints = [0.25, 0.5, 0.75, 1.0]
    snapshots: list[dict[str, float | int | str]] = []
    for checkpoint in checkpoints:
        subset_size = int(len(rows) * checkpoint)
        subset = rows[:subset_size]
        baseline = _group_stats(subset, "outcome_metric")
        cuped = _group_stats(_apply_cuped(subset), "outcome_metric")
        raw_lift = baseline["treatment"].mean - baseline["control"].mean
        cuped_lift = cuped["treatment"].mean - cuped["control"].mean
        raw_z = _z_score(baseline["control"], baseline["treatment"])
        cuped_z = _z_score(cuped["control"], cuped["treatment"])
        snapshots.append(
            {
                "checkpoint": f"{int(checkpoint * 100)}%",
                "users_seen": subset_size,
                "raw_lift": round(raw_lift, 4),
                "raw_p_value": round(_two_sided_p_value(raw_z), 6),
                "cuped_lift": round(cuped_lift, 4),
                "cuped_p_value": round(_two_sided_p_value(cuped_z), 6),
            }
        )
    return snapshots


def build_report(rows: list[ExperimentRow]) -> dict[str, object]:
    raw_stats = _group_stats(rows, "outcome_metric")
    cuped_rows = _apply_cuped(rows)
    cuped_stats = _group_stats(cuped_rows, "outcome_metric")

    raw_z = _z_score(raw_stats["control"], raw_stats["treatment"])
    cuped_z = _z_score(cuped_stats["control"], cuped_stats["treatment"])
    raw_p_value = _two_sided_p_value(raw_z)
    cuped_p_value = _two_sided_p_value(cuped_z)
    raw_lift = raw_stats["treatment"].mean - raw_stats["control"].mean
    cuped_lift = cuped_stats["treatment"].mean - cuped_stats["control"].mean
    cuped_variance_reduction = 1.0 - (
        (cuped_stats["control"].variance + cuped_stats["treatment"].variance)
        / (raw_stats["control"].variance + raw_stats["treatment"].variance)
    )

    recommendation = "ship_treatment" if cuped_p_value < 0.05 and cuped_lift > 0 else "hold"

    return {
        "summary": {
            "users": len(rows),
            "raw_lift": round(raw_lift, 4),
            "raw_p_value": round(raw_p_value, 6),
            "cuped_lift": round(cuped_lift, 4),
            "cuped_p_value": round(cuped_p_value, 6),
            "cuped_variance_reduction": round(cuped_variance_reduction, 4),
            "recommendation": recommendation,
        },
        "group_stats": {
            "raw": {
                "control_mean": round(raw_stats["control"].mean, 4),
                "treatment_mean": round(raw_stats["treatment"].mean, 4),
            },
            "cuped": {
                "control_mean": round(cuped_stats["control"].mean, 4),
                "treatment_mean": round(cuped_stats["treatment"].mean, 4),
            },
        },
        "sequential_snapshots": _sequential_snapshots(rows),
    }


def write_report(report: dict[str, object], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
