from __future__ import annotations

import argparse
import json

from app.analysis import build_report, write_report
from app.config import REPORT_JSON, SIMULATION_CSV
from app.simulation import simulate_rows, write_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Experimentation lab CLI")
    parser.add_argument("command", choices=["simulate", "report"])
    args = parser.parse_args()

    rows = simulate_rows()

    if args.command == "simulate":
        write_rows(rows, SIMULATION_CSV)
        print(
            json.dumps(
                {"generated_csv": str(SIMULATION_CSV), "users": len(rows)},
                indent=2,
            )
        )
        return

    write_rows(rows, SIMULATION_CSV)
    report = build_report(rows)
    write_report(report, REPORT_JSON)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

