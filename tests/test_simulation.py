from __future__ import annotations

from app.simulation import simulate_rows


def test_simulation_is_balanced_and_deterministic() -> None:
    rows = simulate_rows()

    assert len(rows) == 4000
    assert rows[0].user_id == "user_0000"
    assert rows[0].group == "control"
    assert rows[1].group == "treatment"

    control = [row for row in rows if row.group == "control"]
    treatment = [row for row in rows if row.group == "treatment"]

    assert len(control) == len(treatment) == 2000

