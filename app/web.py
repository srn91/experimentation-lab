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
<style>
body{{margin:0;background:#f8fafc;color:#0f172a;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;line-height:1.5}}
main{{max-width:1080px;margin:0 auto;padding:56px 24px}}.hero{{background:linear-gradient(135deg,#111827,#c2410c);color:white;border-radius:22px;padding:38px;box-shadow:0 24px 60px rgba(15,23,42,.18)}}
.eyebrow{{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:#fed7aa;font-weight:700}}h1{{font-size:42px;line-height:1.05;margin:10px 0 14px}}.hero p{{font-size:17px;color:#ffedd5;max-width:780px}}
.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:22px 0}}.card{{background:white;border:1px solid #e2e8f0;border-radius:16px;padding:18px;box-shadow:0 10px 30px rgba(15,23,42,.06)}}
.metric{{font-size:25px;font-weight:800;color:#0f172a}}.label{{font-size:13px;color:#64748b;margin-top:3px}}.links{{display:flex;flex-wrap:wrap;gap:12px;margin-top:22px}}
a.button{{background:#0f172a;color:white;text-decoration:none;padding:11px 14px;border-radius:10px;font-weight:700}}a.secondary{{background:white;color:#0f172a;border:1px solid #cbd5e1}}
@media(max-width:800px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}h1{{font-size:34px}}}}
</style></head>
<body><main>
<section class="hero"><div class="eyebrow">Experimentation system</div><h1>Experimentation Lab</h1>
<p>A/B testing workflow with reproducible assignment, CUPED variance reduction, observed power, and decision output.</p>
<div class="links"><a class="button" href="/summary">Experiment summary</a><a class="button secondary" href="/report">Full report</a><a class="button secondary" href="/docs">API docs</a></div></section>
<section class="grid">
<div class="card"><div class="metric">{users}</div><div class="label">users analyzed</div></div>
<div class="card"><div class="metric">CUPED</div><div class="label">variance reduction</div></div>
<div class="card"><div class="metric">MDE</div><div class="label">effect planning</div></div>
<div class="card"><div class="metric">ship</div><div class="label">decision output</div></div>
</section>
<section class="card"><p>The summary endpoint shows lift, p-values, variance reduction, power, guardrails, and the final recommendation.</p></section>
</main></body></html>"""

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
