from __future__ import annotations

import json

from app import cli


def test_cli_simulate_writes_csv(monkeypatch, tmp_path, capsys) -> None:
    csv_path = tmp_path / "experiment_assignments.csv"
    monkeypatch.setattr(cli, "SIMULATION_CSV", csv_path)
    monkeypatch.setattr(cli, "REPORT_JSON", tmp_path / "decision_report.json")
    monkeypatch.setattr("sys.argv", ["app.cli", "simulate"])

    cli.main()

    captured = json.loads(capsys.readouterr().out)
    assert captured["generated_csv"] == str(csv_path)
    assert captured["users"] == 4000
    assert csv_path.exists()


def test_cli_report_writes_json(monkeypatch, tmp_path, capsys) -> None:
    csv_path = tmp_path / "experiment_assignments.csv"
    report_path = tmp_path / "decision_report.json"
    monkeypatch.setattr(cli, "SIMULATION_CSV", csv_path)
    monkeypatch.setattr(cli, "REPORT_JSON", report_path)
    monkeypatch.setattr("sys.argv", ["app.cli", "report"])

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["users"] == 4000
    assert payload["summary"]["recommendation"] == "ship_treatment"
    assert report_path.exists()
    stored_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert stored_report["summary"]["cuped_variance_reduction"] == payload["summary"]["cuped_variance_reduction"]
