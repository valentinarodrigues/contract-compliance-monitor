"""
Contract Compliance Monitor — CLI entry point

Usage:
  python main.py monitor              # Run one monitoring cycle and print results
  python main.py monitor --watch      # Run continuously (polls every POLLING_INTERVAL_SECONDS)
  python main.py parse <contract.txt> # Parse a contract file and print extracted SLA terms
  python main.py report <vendor_id>   # Generate and print a compliance report
  python main.py dashboard            # Start the web dashboard (http://localhost:8000)
  python main.py status               # Show current system status
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def _build_monitor():
    from config import settings
    from src.alerting.alert_manager import AlertManager
    from src.ingestion.factory import create_log_source
    from src.models import Contract
    from src.monitoring.compliance_monitor import ComplianceMonitor
    from src.parsers.factory import create_parser

    log_source = create_log_source()
    contracts: dict[str, Contract] = {}

    contract_dir = Path("data/sample_contracts")
    for contract_file in contract_dir.glob("*.txt"):
        vendor_id = contract_file.stem
        contract_text = contract_file.read_text()
        parser = create_parser(vendor_id=vendor_id)
        sla_terms = parser.extract_sla_terms(contract_text)

        first_line = contract_text.split("\n")[0]
        vendor_name = first_line.replace("VENDOR:", "").strip() if "VENDOR:" in first_line else vendor_id

        contracts[vendor_id] = Contract(
            id=f"contract_{vendor_id}",
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            contract_text=contract_text,
            sla_terms=sla_terms,
        )
        logger.info(
            "Loaded contract for %s (%d SLA terms)", vendor_name, len(sla_terms)
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


def cmd_monitor(watch: bool = False):
    monitor = _build_monitor()
    if watch:
        logger.info("Starting continuous monitoring... (Ctrl+C to stop)")
        monitor.run_continuous()
    else:
        violations = monitor.run_once(lookback_hours=24)
        print(f"\n{'='*60}")
        print(f"Monitoring cycle complete: {len(violations)} violations detected")
        for v in violations:
            print(f"  [{v.severity.value.upper()}] {v.vendor_name} — {v.sla_term_name}: "
                  f"{v.metric}={v.actual_value} (threshold: {v.operator}{v.threshold})")
        if not violations:
            print("  All SLA terms within contract bounds.")
        print(f"{'='*60}\n")


def cmd_parse(contract_file: str):
    from src.parsers.factory import create_parser

    path = Path(contract_file)
    if not path.exists():
        print(f"Error: file not found: {contract_file}", file=sys.stderr)
        sys.exit(1)

    contract_text = path.read_text()
    vendor_id = path.stem
    parser = create_parser(vendor_id=vendor_id)
    terms = parser.extract_sla_terms(contract_text)

    print(f"\nExtracted {len(terms)} SLA terms from {path.name}:\n")
    for term in terms:
        print(json.dumps(term.to_dict(), indent=2))


def cmd_report(vendor_id: str):
    from src.alerting.report_generator import ReportGenerator

    monitor = _build_monitor()
    contract = monitor.contracts.get(vendor_id)
    if not contract:
        print(f"Error: vendor '{vendor_id}' not found", file=sys.stderr)
        print(f"Available vendors: {list(monitor.contracts.keys())}")
        sys.exit(1)

    monitor.run_once(lookback_hours=24)
    violations = monitor.get_violations(vendor_id=vendor_id)

    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=30)

    report = ReportGenerator().generate(contract, violations, period_start, period_end)
    print(ReportGenerator().to_text(report))


def cmd_dashboard():
    import uvicorn
    from config import settings

    logger.info("Starting dashboard at http://%s:%d", settings.DASHBOARD_HOST, settings.DASHBOARD_PORT)
    uvicorn.run(
        "src.dashboard.app:app",
        host=settings.DASHBOARD_HOST,
        port=settings.DASHBOARD_PORT,
        reload=False,
        log_level="info",
    )


def cmd_status():
    monitor = _build_monitor()
    monitor.run_once(lookback_hours=1)
    status = monitor.status()
    print(json.dumps(status, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Contract Compliance Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    # monitor
    p_monitor = sub.add_parser("monitor", help="Run compliance monitoring")
    p_monitor.add_argument("--watch", action="store_true", help="Run continuously")

    # parse
    p_parse = sub.add_parser("parse", help="Parse a contract file")
    p_parse.add_argument("contract_file", help="Path to contract text file")

    # report
    p_report = sub.add_parser("report", help="Generate compliance report")
    p_report.add_argument("vendor_id", help="Vendor ID to report on")

    # dashboard
    sub.add_parser("dashboard", help="Start the web dashboard")

    # status
    sub.add_parser("status", help="Show system status")

    args = parser.parse_args()

    if args.command == "monitor":
        cmd_monitor(watch=args.watch)
    elif args.command == "parse":
        cmd_parse(args.contract_file)
    elif args.command == "report":
        cmd_report(args.vendor_id)
    elif args.command == "dashboard":
        cmd_dashboard()
    elif args.command == "status":
        cmd_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
