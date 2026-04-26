from __future__ import annotations

import json

from fastapi.testclient import TestClient

import app.web as web

app = web.app


def test_health_report_summary_endpoints() -> None:
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    health_payload = health.json()
    assert health_payload["status"] == "ok"
    assert health_payload["service"] == "experimentation-lab"

    report = client.get("/report")
    assert report.status_code == 200
    report_payload = report.json()
    assert report_payload["summary"]["users"] == 4000
    assert report_payload["summary"]["guardrail_status"] == "pass"
    assert report_payload["summary"]["recommendation"] == "ship_treatment"
    assert report_payload["guardrails"]["metrics"]["support_contact_rate"]["status"] == "pass"
    assert len(report_payload["segment_breakdowns"]) == 3

    summary = client.get("/summary")
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["users"] == 4000
    assert summary_payload["guardrail_status"] == "pass"
    assert summary_payload["recommendation"] == "ship_treatment"


def test_serves_existing_report_artifact(monkeypatch, tmp_path) -> None:
    report_path = tmp_path / "decision_report.json"
    payload = {
        "summary": {"users": 1, "recommendation": "hold"},
        "group_stats": {},
        "sequential_snapshots": [],
    }
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(web, "REPORT_JSON", report_path)

    client = TestClient(web.create_app())

    response = client.get("/report")
    assert response.status_code == 200
    assert response.json() == payload
