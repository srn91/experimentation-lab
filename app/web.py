from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException

from app.analysis import build_report
from app.config import REPORT_JSON
from app.simulation import simulate_rows

SERVICE_NAME = "experimentation-lab"


def _load_report() -> dict[str, object]:
    if REPORT_JSON.exists():
        return json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    return build_report(simulate_rows())


def create_app() -> FastAPI:
    app = FastAPI(
        title="experimentation-lab",
        version="1.0.0",
        description="Read-only experiment decision surface for Render deployment.",
    )

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": SERVICE_NAME,
            "report_ready": REPORT_JSON.exists(),
            "report_path": str(REPORT_JSON),
        }

    @app.get("/report")
    def report() -> dict[str, object]:
        payload = _load_report()
        if "summary" not in payload:
            raise HTTPException(status_code=500, detail="report payload is invalid")
        return payload

    @app.get("/summary")
    def summary() -> dict[str, object]:
        payload = _load_report()
        summary_payload = payload.get("summary")
        if not isinstance(summary_payload, dict):
            raise HTTPException(status_code=500, detail="summary payload is invalid")
        return summary_payload

    return app


app = create_app()
