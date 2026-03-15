from __future__ import annotations
import json
import logging
from datetime import datetime
from src.models import ComplianceReport, Contract, Severity, Violation

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates compliance reports for a vendor over a time period."""

    def generate(
        self,
        contract: Contract,
        violations: list[Violation],
        period_start: datetime,
        period_end: datetime,
        total_checks: int = 100,
    ) -> ComplianceReport:
        """
        Build a ComplianceReport.

        total_checks is the number of SLA evaluation windows in the period,
        used to compute the compliance rate.
        """
        vendor_violations = [
            v for v in violations if v.vendor_id == contract.vendor_id and not v.resolved
        ]

        critical = sum(1 for v in vendor_violations if v.severity == Severity.CRITICAL)
        warnings = sum(1 for v in vendor_violations if v.severity == Severity.WARNING)

        # Compliance rate: fraction of checks without a critical violation
        compliance_rate = max(
            0.0,
            100.0 * (1 - critical / max(total_checks, 1)),
        )

        report = ComplianceReport(
            vendor_id=contract.vendor_id,
            vendor_name=contract.vendor_name,
            period_start=period_start,
            period_end=period_end,
            total_violations=len(vendor_violations),
            critical_violations=critical,
            warning_violations=warnings,
            violations=vendor_violations,
            sla_compliance_rate=round(compliance_rate, 2),
        )

        logger.info(
            "Report generated for vendor=%s: %d violations (%.1f%% compliance)",
            contract.vendor_id,
            len(vendor_violations),
            compliance_rate,
        )
        return report

    def to_json(self, report: ComplianceReport, indent: int = 2) -> str:
        return json.dumps(report.to_dict(), indent=indent)

    def to_text(self, report: ComplianceReport) -> str:
        lines = [
            "=" * 60,
            f"COMPLIANCE REPORT — {report.vendor_name}",
            "=" * 60,
            f"Period      : {report.period_start.date()} → {report.period_end.date()}",
            f"Generated   : {report.generated_at.isoformat()}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Compliance Rate    : {report.sla_compliance_rate}%",
            f"Total Violations   : {report.total_violations}",
            f"  Critical         : {report.critical_violations}",
            f"  Warning          : {report.warning_violations}",
            "",
        ]

        if report.violations:
            lines.append("VIOLATIONS")
            lines.append("-" * 40)
            for v in report.violations:
                lines.append(
                    f"  [{v.severity.value.upper()}] {v.sla_term_name} | "
                    f"{v.metric} = {v.actual_value} (threshold: {v.operator} {v.threshold}) | "
                    f"{v.detection_method} | {v.detected_at.strftime('%Y-%m-%d %H:%M')}"
                )
        else:
            lines.append("No violations detected. Full SLA compliance.")

        lines.append("=" * 60)
        return "\n".join(lines)
