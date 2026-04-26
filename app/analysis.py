from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import NormalDist

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


def _rows_for_segment(rows: list[ExperimentRow], segment: str) -> list[ExperimentRow]:
    return [row for row in rows if row.segment == segment]


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


def _normal_ppf(probability: float) -> float:
    return NormalDist().inv_cdf(probability)


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
                segment=row.segment,
                pre_metric=row.pre_metric,
                outcome_metric=row.outcome_metric - theta * (row.pre_metric - pre_mean),
                guardrail_contact_rate=row.guardrail_contact_rate,
                guardrail_latency_ms=row.guardrail_latency_ms,
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


def _minimum_detectable_effect(
    control: GroupStats,
    treatment: GroupStats,
    *,
    alpha: float,
    target_power: float,
) -> float:
    standard_error = math.sqrt(
        (control.variance / control.users) + (treatment.variance / treatment.users)
    )
    z_alpha = _normal_ppf(1.0 - (alpha / 2.0))
    z_beta = _normal_ppf(target_power)
    return (z_alpha + z_beta) * standard_error


def _observed_power(effect: float, standard_error: float, *, alpha: float) -> float:
    if standard_error == 0:
        raise ValueError("standard error is zero; cannot compute observed power")
    critical_value = _normal_ppf(1.0 - (alpha / 2.0))
    non_centrality = abs(effect) / standard_error
    return 1.0 - _normal_cdf(critical_value - non_centrality) + _normal_cdf(
        -critical_value - non_centrality
    )


def _required_users_per_group(
    *,
    variance_sum: float,
    effect: float,
    alpha: float,
    target_power: float,
) -> int | None:
    if effect == 0:
        return None
    z_alpha = _normal_ppf(1.0 - (alpha / 2.0))
    z_beta = _normal_ppf(target_power)
    return math.ceil((((z_alpha + z_beta) ** 2) * variance_sum) / (effect ** 2))


def _guardrail_metrics(rows: list[ExperimentRow]) -> dict[str, object]:
    thresholds = {
        "contact_rate_increase_max": 0.01,
        "latency_increase_ms_max": 8.0,
    }
    contact_stats = _group_stats(rows, "guardrail_contact_rate")
    latency_stats = _group_stats(rows, "guardrail_latency_ms")

    contact_delta = contact_stats["treatment"].mean - contact_stats["control"].mean
    latency_delta = latency_stats["treatment"].mean - latency_stats["control"].mean

    contact_status = "pass" if contact_delta <= thresholds["contact_rate_increase_max"] else "fail"
    latency_status = "pass" if latency_delta <= thresholds["latency_increase_ms_max"] else "fail"

    overall_status = "pass" if contact_status == "pass" and latency_status == "pass" else "fail"

    return {
        "overall_status": overall_status,
        "metrics": {
            "support_contact_rate": {
                "control_mean": round(contact_stats["control"].mean, 4),
                "treatment_mean": round(contact_stats["treatment"].mean, 4),
                "delta": round(contact_delta, 4),
                "max_allowed_increase": thresholds["contact_rate_increase_max"],
                "status": contact_status,
                "direction": "lower_is_better",
            },
            "p95_checkout_latency_ms": {
                "control_mean": round(latency_stats["control"].mean, 4),
                "treatment_mean": round(latency_stats["treatment"].mean, 4),
                "delta": round(latency_delta, 4),
                "max_allowed_increase": thresholds["latency_increase_ms_max"],
                "status": latency_status,
                "direction": "lower_is_better",
            },
        },
    }


def _segment_breakdowns(rows: list[ExperimentRow]) -> list[dict[str, object]]:
    breakdowns: list[dict[str, object]] = []
    for segment in sorted({row.segment for row in rows}):
        segment_rows = _rows_for_segment(rows, segment)
        raw_stats = _group_stats(segment_rows, "outcome_metric")
        cuped_rows = _apply_cuped(segment_rows)
        cuped_stats = _group_stats(cuped_rows, "outcome_metric")
        cuped_lift = cuped_stats["treatment"].mean - cuped_stats["control"].mean
        cuped_z = _z_score(cuped_stats["control"], cuped_stats["treatment"])
        cuped_p_value = _two_sided_p_value(cuped_z)
        breakdowns.append(
            {
                "segment": segment,
                "users": len(segment_rows),
                "raw_lift": round(raw_stats["treatment"].mean - raw_stats["control"].mean, 4),
                "cuped_lift": round(cuped_lift, 4),
                "cuped_p_value": round(cuped_p_value, 6),
                "recommendation": "ship_treatment" if cuped_p_value < 0.05 and cuped_lift > 0 else "hold",
            }
        )
    return breakdowns


def build_report(rows: list[ExperimentRow]) -> dict[str, object]:
    alpha = 0.05
    target_power = 0.8
    raw_stats = _group_stats(rows, "outcome_metric")
    cuped_rows = _apply_cuped(rows)
    cuped_stats = _group_stats(cuped_rows, "outcome_metric")

    raw_z = _z_score(raw_stats["control"], raw_stats["treatment"])
    cuped_z = _z_score(cuped_stats["control"], cuped_stats["treatment"])
    raw_p_value = _two_sided_p_value(raw_z)
    cuped_p_value = _two_sided_p_value(cuped_z)
    raw_lift = raw_stats["treatment"].mean - raw_stats["control"].mean
    cuped_lift = cuped_stats["treatment"].mean - cuped_stats["control"].mean
    cuped_standard_error = math.sqrt(
        (cuped_stats["control"].variance / cuped_stats["control"].users)
        + (cuped_stats["treatment"].variance / cuped_stats["treatment"].users)
    )
    cuped_variance_reduction = 1.0 - (
        (cuped_stats["control"].variance + cuped_stats["treatment"].variance)
        / (raw_stats["control"].variance + raw_stats["treatment"].variance)
    )
    minimum_detectable_effect = _minimum_detectable_effect(
        cuped_stats["control"],
        cuped_stats["treatment"],
        alpha=alpha,
        target_power=target_power,
    )
    observed_power = _observed_power(cuped_lift, cuped_standard_error, alpha=alpha)
    required_users_per_group = _required_users_per_group(
        variance_sum=cuped_stats["control"].variance + cuped_stats["treatment"].variance,
        effect=abs(cuped_lift),
        alpha=alpha,
        target_power=target_power,
    )
    guardrails = _guardrail_metrics(rows)
    recommendation = (
        "ship_treatment"
        if cuped_p_value < 0.05 and cuped_lift > 0 and guardrails["overall_status"] == "pass"
        else "hold"
    )

    return {
        "summary": {
            "users": len(rows),
            "raw_lift": round(raw_lift, 4),
            "raw_p_value": round(raw_p_value, 6),
            "cuped_lift": round(cuped_lift, 4),
            "cuped_p_value": round(cuped_p_value, 6),
            "cuped_variance_reduction": round(cuped_variance_reduction, 4),
            "minimum_detectable_effect": round(minimum_detectable_effect, 4),
            "observed_power": round(observed_power, 4),
            "guardrail_status": guardrails["overall_status"],
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
        "power_analysis": {
            "alpha": alpha,
            "target_power": target_power,
            "minimum_detectable_effect": round(minimum_detectable_effect, 4),
            "observed_power": round(observed_power, 4),
            "required_users_per_group_at_observed_effect": required_users_per_group,
            "current_users_per_group": cuped_stats["control"].users,
        },
        "guardrails": guardrails,
        "segment_breakdowns": _segment_breakdowns(rows),
        "sequential_snapshots": _sequential_snapshots(rows),
    }


def write_report(report: dict[str, object], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
