from __future__ import annotations

from app.analysis import build_report
from app.simulation import simulate_rows


def test_report_recommends_treatment_and_reduces_variance() -> None:
    report = build_report(simulate_rows())
    summary = report["summary"]

    assert summary["users"] == 4000
    assert summary["recommendation"] == "ship_treatment"
    assert summary["cuped_p_value"] < 0.05
    assert summary["cuped_variance_reduction"] > 0.3


def test_sequential_snapshots_cover_full_run() -> None:
    report = build_report(simulate_rows())
    snapshots = report["sequential_snapshots"]

    assert [snapshot["checkpoint"] for snapshot in snapshots] == ["25%", "50%", "75%", "100%"]
    assert snapshots[-1]["users_seen"] == 4000

