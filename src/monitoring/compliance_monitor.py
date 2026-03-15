from __future__ import annotations
import logging
import time
from datetime import datetime, timedelta
from src.ingestion.base import BaseLogSource
from src.models import Contract, Violation
from src.monitoring.anomaly_detector import AnomalyDetector
from src.monitoring.rule_engine import RuleEngine

logger = logging.getLogger(__name__)


class ComplianceMonitor:
    """
    Orchestrates the full compliance monitoring pipeline:

      1. Fetch logs from the configured log source
      2. Run rule-based violation detection against SLA thresholds
      3. Run ML-based anomaly detection on usage patterns
      4. Notify registered violation handlers (e.g., AlertManager)
    """

    def __init__(
        self,
        log_source: BaseLogSource,
        contracts: dict[str, Contract],
        polling_interval: int = 60,
        lookback_hours: float = 1.0,
        anomaly_contamination: float = 0.05,
        min_samples_for_anomaly: int = 20,
    ):
        self.log_source = log_source
        self.contracts = contracts  # vendor_id -> Contract
        self.polling_interval = polling_interval
        self.lookback_hours = lookback_hours
        self.rule_engine = RuleEngine()
        self.anomaly_detector = AnomalyDetector(
            contamination=anomaly_contamination,
            min_samples=min_samples_for_anomaly,
        )
        self._violation_handlers: list = []
        self.all_violations: list[Violation] = []

    def register_handler(self, handler) -> None:
        """Register a callable(violations: list[Violation]) to be called on new violations."""
        self._violation_handlers.append(handler)

    def run_once(self, lookback_hours: float | None = None) -> list[Violation]:
        """
        Execute one monitoring cycle and return detected violations.
        """
        hours = lookback_hours or self.lookback_hours
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        logger.info(
            "Running compliance check: window=[%s, %s]",
            start_time.isoformat(),
            end_time.isoformat(),
        )

        new_violations: list[Violation] = []

        for vendor_id, contract in self.contracts.items():
            try:
                logs = self.log_source.fetch_logs(vendor_id, start_time, end_time)
                logger.info("Fetched %d log events for vendor '%s'", len(logs), vendor_id)

                if not logs:
                    continue

                # Rule-based detection
                rule_violations = self.rule_engine.check(
                    contract, logs, start_time, end_time
                )
                new_violations.extend(rule_violations)

                # Anomaly detection
                anomaly_violations = self.anomaly_detector.check(contract, logs)
                new_violations.extend(anomaly_violations)

            except Exception as exc:
                logger.error("Error processing vendor '%s': %s", vendor_id, exc, exc_info=True)

        self.all_violations.extend(new_violations)

        if new_violations:
            for handler in self._violation_handlers:
                try:
                    handler(new_violations)
                except Exception as exc:
                    logger.error("Violation handler failed: %s", exc)

        logger.info(
            "Cycle complete: %d new violations (total %d)",
            len(new_violations),
            len(self.all_violations),
        )
        return new_violations

    def run_continuous(self) -> None:
        """
        Run the monitoring loop indefinitely.
        Blocks the calling thread — run in a background thread/process for the dashboard.
        """
        logger.info(
            "Starting continuous monitoring (interval=%ds, vendors=%s)",
            self.polling_interval,
            list(self.contracts.keys()),
        )
        while True:
            self.run_once()
            time.sleep(self.polling_interval)

    def get_violations(
        self,
        vendor_id: str | None = None,
        severity: str | None = None,
        resolved: bool | None = None,
    ) -> list[Violation]:
        """Filter the accumulated violation log."""
        result = self.all_violations
        if vendor_id:
            result = [v for v in result if v.vendor_id == vendor_id]
        if severity:
            result = [v for v in result if v.severity.value == severity]
        if resolved is not None:
            result = [v for v in result if v.resolved == resolved]
        return result

    def resolve_violation(self, violation_id: str) -> bool:
        for v in self.all_violations:
            if v.id == violation_id:
                v.resolved = True
                return True
        return False

    def status(self) -> dict:
        total = len(self.all_violations)
        open_violations = [v for v in self.all_violations if not v.resolved]
        critical = sum(1 for v in open_violations if v.severity.value == "critical")
        return {
            "vendors_monitored": len(self.contracts),
            "total_violations": total,
            "open_violations": len(open_violations),
            "critical_violations": critical,
            "warning_violations": len(open_violations) - critical,
        }
