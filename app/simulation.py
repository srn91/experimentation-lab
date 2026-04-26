from __future__ import annotations

import csv
import random
from pathlib import Path

from app.models import ExperimentRow


def simulate_rows(seed: int = 20260426, users: int = 4000) -> list[ExperimentRow]:
    generator = random.Random(seed)
    rows: list[ExperimentRow] = []
    segments = ["new_user", "repeat_buyer", "high_value"]
    for index in range(users):
        user_id = f"user_{index:04d}"
        segment = segments[index % len(segments)]
        pre_metric = max(0.0, generator.gauss(100.0, 18.0))
        group = "treatment" if index % 2 else "control"
        baseline_noise = generator.gauss(0.0, 12.0)
        segment_outcome_boost = {"new_user": -3.0, "repeat_buyer": 0.0, "high_value": 5.5}[segment]
        treatment_effect = {"new_user": 4.8, "repeat_buyer": 6.2, "high_value": 7.9}[segment] if group == "treatment" else 0.0
        outcome_metric = max(0.0, (0.72 * pre_metric) + 18.0 + treatment_effect + baseline_noise)
        contact_rate = max(
            0.0,
            min(
                1.0,
                0.08
                + (0.018 if segment == "new_user" else 0.0)
                - (0.009 if group == "treatment" else 0.0)
                + generator.gauss(0.0, 0.01),
            ),
        )
        latency_ms = max(
            40.0,
            180.0
            + (16.0 if segment == "high_value" else 0.0)
            + (4.0 if group == "treatment" else 0.0)
            + generator.gauss(0.0, 9.0),
        )
        rows.append(
            ExperimentRow(
                user_id=user_id,
                group=group,
                segment=segment,
                pre_metric=round(pre_metric, 4),
                outcome_metric=round(outcome_metric + segment_outcome_boost, 4),
                guardrail_contact_rate=round(contact_rate, 4),
                guardrail_latency_ms=round(latency_ms, 4),
            )
        )
    return rows


def write_rows(rows: list[ExperimentRow], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "user_id",
                "group",
                "segment",
                "pre_metric",
                "outcome_metric",
                "guardrail_contact_rate",
                "guardrail_latency_ms",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.user_id,
                    row.group,
                    row.segment,
                    row.pre_metric,
                    row.outcome_metric,
                    row.guardrail_contact_rate,
                    row.guardrail_latency_ms,
                ]
            )
