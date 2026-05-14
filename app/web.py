from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

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

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        summary_payload = _load_report().get("summary", {})
        users = summary_payload.get("users", "available")
        return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Experimentation Lab</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;max-width:860px;margin:48px auto;padding:0 24px;line-height:1.5;color:#111}}a{{color:#0645ad}}</style></head>
<body>
<h1>Experimentation Lab</h1>
<p>A/B testing workflow with reproducible assignment, CUPED variance reduction, observed power, and decision output.</p>
<ul><li>Users analyzed: {users}</li></ul>
<h2>Open endpoints</h2>
<ul>
<li><a href="/summary">Experiment summary</a></li>
<li><a href="/report">Full report JSON</a></li>
<li><a href="/health">Health check</a></li>
<li><a href="/docs">API docs</a></li>
</ul>
</body></html>"""

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
