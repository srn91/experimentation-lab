from __future__ import annotations

import csv
import random
from pathlib import Path

from app.models import ExperimentRow


def simulate_rows(seed: int = 20260426, users: int = 4000) -> list[ExperimentRow]:
    generator = random.Random(seed)
    rows: list[ExperimentRow] = []
    for index in range(users):
        user_id = f"user_{index:04d}"
        pre_metric = max(0.0, generator.gauss(100.0, 18.0))
        group = "treatment" if index % 2 else "control"
        baseline_noise = generator.gauss(0.0, 12.0)
        treatment_effect = 6.5 if group == "treatment" else 0.0
        outcome_metric = max(0.0, (0.72 * pre_metric) + 18.0 + treatment_effect + baseline_noise)
        rows.append(
            ExperimentRow(
                user_id=user_id,
                group=group,
                pre_metric=round(pre_metric, 4),
                outcome_metric=round(outcome_metric, 4),
            )
        )
    return rows


def write_rows(rows: list[ExperimentRow], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["user_id", "group", "pre_metric", "outcome_metric"])
        for row in rows:
            writer.writerow([row.user_id, row.group, row.pre_metric, row.outcome_metric])
