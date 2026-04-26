from __future__ import annotations

from app.analysis import build_report
from app.simulation import simulate_rows


def test_report_recommends_treatment_and_reduces_variance() -> None:
    report = build_report(simulate_rows())
    summary = report["summary"]
    power = report["power_analysis"]
    guardrails = report["guardrails"]

    assert summary["users"] == 4000
    assert summary["guardrail_status"] == "pass"
    assert summary["recommendation"] == "ship_treatment"
    assert summary["cuped_p_value"] < 0.05
    assert summary["cuped_variance_reduction"] > 0.3
    assert summary["observed_power"] > 0.99
    assert summary["minimum_detectable_effect"] > 0
    assert power["required_users_per_group_at_observed_effect"] < power["current_users_per_group"]
    assert guardrails["metrics"]["support_contact_rate"]["delta"] < 0
    assert guardrails["metrics"]["p95_checkout_latency_ms"]["delta"] < 8.0


def test_sequential_snapshots_cover_full_run() -> None:
    report = build_report(simulate_rows())
    snapshots = report["sequential_snapshots"]

    assert [snapshot["checkpoint"] for snapshot in snapshots] == ["25%", "50%", "75%", "100%"]
    assert snapshots[-1]["users_seen"] == 4000


def test_power_analysis_is_exposed_in_report() -> None:
    report = build_report(simulate_rows())

    assert report["power_analysis"]["alpha"] == 0.05
    assert report["power_analysis"]["target_power"] == 0.8
    assert report["power_analysis"]["minimum_detectable_effect"] == report["summary"]["minimum_detectable_effect"]


def test_segment_breakdowns_are_exposed_in_report() -> None:
    report = build_report(simulate_rows())
    segments = report["segment_breakdowns"]

    assert [segment["segment"] for segment in segments] == [
        "high_value",
        "new_user",
        "repeat_buyer",
    ]
    assert all(segment["users"] >= 1333 for segment in segments)
    assert all(segment["recommendation"] == "ship_treatment" for segment in segments)
