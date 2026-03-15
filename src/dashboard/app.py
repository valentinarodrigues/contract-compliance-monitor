from __future__ import annotations
import sys
import os

# Ensure project root is on the path when running the dashboard directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import threading
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.alerting.alert_manager import AlertManager
from src.alerting.report_generator import ReportGenerator
from src.ingestion.factory import create_log_source
from src.models import Contract
from src.monitoring.compliance_monitor import ComplianceMonitor
from src.parsers.factory import create_parser

TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="Contract Compliance Monitor", version="1.0.0")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ─── Global state (shared between monitor thread and API) ─────────────────────
_monitor: ComplianceMonitor | None = None
_contracts: dict[str, Contract] = {}


def _build_monitor() -> ComplianceMonitor:
    from config import settings

    log_source = create_log_source()

    # Load and parse contracts for each vendor
    contracts: dict[str, Contract] = {}
    contract_dir = Path("data/sample_contracts")

    for contract_file in contract_dir.glob("*.txt"):
        vendor_id = contract_file.stem  # e.g. vendor_a
        contract_text = contract_file.read_text()
        parser = create_parser(vendor_id=vendor_id)
        sla_terms = parser.extract_sla_terms(contract_text)

        contracts[vendor_id] = Contract(
            id=f"contract_{vendor_id}",
            vendor_id=vendor_id,
            vendor_name=contract_text.split("\n")[0].replace("VENDOR:", "").strip(),
            contract_text=contract_text,
            sla_terms=sla_terms,
        )

    alert_manager = AlertManager()
    monitor = ComplianceMonitor(
        log_source=log_source,
        contracts=contracts,
        polling_interval=settings.POLLING_INTERVAL_SECONDS,
        anomaly_contamination=settings.ANOMALY_CONTAMINATION,
        min_samples_for_anomaly=settings.MIN_SAMPLES_FOR_ANOMALY,
    )
    monitor.register_handler(alert_manager)
    return monitor


@app.on_event("startup")
def startup_event():
    global _monitor, _contracts
    _monitor = _build_monitor()
    _contracts = _monitor.contracts

    # Run an initial check to populate data
    _monitor.run_once(lookback_hours=24)

    # Start background polling thread
    t = threading.Thread(target=_monitor.run_continuous, daemon=True)
    t.start()


# ─── HTML Routes ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard_home(request: Request):
    status = _monitor.status() if _monitor else {}
    violations = (_monitor.get_violations() if _monitor else [])[-20:]
    vendors = list(_contracts.values())
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "status": status,
            "recent_violations": [v.to_dict() for v in reversed(violations)],
            "vendors": [c.to_dict() for c in vendors],
            "now": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        },
    )


@app.get("/violations", response_class=HTMLResponse)
def violations_page(request: Request, vendor_id: str = "", severity: str = ""):
    violations = _monitor.get_violations(
        vendor_id=vendor_id or None,
        severity=severity or None,
    ) if _monitor else []
    vendors = list(_contracts.keys())
    return templates.TemplateResponse(
        "violations.html",
        {
            "request": request,
            "violations": [v.to_dict() for v in reversed(violations)],
            "vendors": vendors,
            "filter_vendor": vendor_id,
            "filter_severity": severity,
        },
    )


@app.get("/report/{vendor_id}", response_class=HTMLResponse)
def report_page(request: Request, vendor_id: str):
    contract = _contracts.get(vendor_id)
    if not contract:
        return HTMLResponse(f"<h1>Vendor '{vendor_id}' not found</h1>", status_code=404)

    violations = _monitor.get_violations(vendor_id=vendor_id) if _monitor else []
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=30)

    report = ReportGenerator().generate(contract, violations, period_start, period_end)
    return templates.TemplateResponse(
        "report.html",
        {"request": request, "report": report.to_dict(), "contract": contract.to_dict()},
    )


# ─── JSON API Routes ──────────────────────────────────────────────────────────

@app.get("/api/status")
def api_status():
    return _monitor.status() if _monitor else {"error": "monitor not initialized"}


@app.get("/api/violations")
def api_violations(vendor_id: str = "", severity: str = "", resolved: str = ""):
    resolved_filter = None
    if resolved == "true":
        resolved_filter = True
    elif resolved == "false":
        resolved_filter = False

    violations = _monitor.get_violations(
        vendor_id=vendor_id or None,
        severity=severity or None,
        resolved=resolved_filter,
    ) if _monitor else []
    return JSONResponse([v.to_dict() for v in violations])


@app.get("/api/vendors")
def api_vendors():
    return JSONResponse([c.to_dict() for c in _contracts.values()])


@app.get("/api/report/{vendor_id}")
def api_report(vendor_id: str):
    contract = _contracts.get(vendor_id)
    if not contract:
        return JSONResponse({"error": f"Vendor '{vendor_id}' not found"}, status_code=404)

    violations = _monitor.get_violations(vendor_id=vendor_id) if _monitor else []
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=30)
    report = ReportGenerator().generate(contract, violations, period_start, period_end)
    return JSONResponse(report.to_dict())


@app.post("/api/violations/{violation_id}/resolve")
def resolve_violation(violation_id: str):
    if _monitor and _monitor.resolve_violation(violation_id):
        return JSONResponse({"status": "resolved"})
    return JSONResponse({"error": "violation not found"}, status_code=404)
