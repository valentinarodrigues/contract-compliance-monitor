from __future__ import annotations
import logging
from collections import defaultdict
from datetime import datetime
from src.models import Contract, LogEvent, Severity, Violation

logger = logging.getLogger(__name__)

try:
    import numpy as np
    from sklearn.ensemble import IsolationForest
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not installed — anomaly detection disabled")


class AnomalyDetector:
    """
    Detects anomalous usage patterns using Isolation Forest.

    Maintains a per-vendor, per-metric history buffer and trains a model
    once MIN_SAMPLES_FOR_ANOMALY events have been collected.
    Anomalies that also look like SLA violations are emitted as Violations.
    """

    def __init__(self, contamination: float = 0.05, min_samples: int = 20):
        self.contamination = contamination
        self.min_samples = min_samples
        # history[vendor_id][metric] -> list of (timestamp, value)
        self._history: dict[str, dict[str, list[tuple[datetime, float]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        # Trained models per vendor+metric
        self._models: dict[tuple[str, str], IsolationForest] = {}

    def ingest(self, logs: list[LogEvent]) -> None:
        """Add new log events to the history buffer."""
        for event in logs:
            self._history[event.vendor_id][event.metric].append(
                (event.timestamp, event.value)
            )

    def check(self, contract: Contract, logs: list[LogEvent]) -> list[Violation]:
        """Detect anomalous events in `logs` for the given contract."""
        if not _SKLEARN_AVAILABLE:
            return []

        self.ingest(logs)
        violations: list[Violation] = []
        known_metrics = {term.metric for term in contract.sla_terms}

        for metric in known_metrics:
            history = self._history[contract.vendor_id].get(metric, [])
            if len(history) < self.min_samples:
                logger.debug(
                    "Insufficient history for anomaly detection: vendor=%s metric=%s (%d/%d)",
                    contract.vendor_id,
                    metric,
                    len(history),
                    self.min_samples,
                )
                continue

            model_key = (contract.vendor_id, metric)
            values = np.array([v for _, v in history]).reshape(-1, 1)

            # Retrain model with latest history
            model = IsolationForest(
                contamination=self.contamination,
                random_state=42,
                n_estimators=100,
            )
            model.fit(values)
            self._models[model_key] = model

            # Score only the new batch of logs
            new_events = [e for e in logs if e.metric == metric]
            if not new_events:
                continue

            new_values = np.array([e.value for e in new_events]).reshape(-1, 1)
            scores = model.predict(new_values)  # -1 = anomaly, 1 = normal

            for event, score in zip(new_events, scores):
                if score == -1:
                    violations.append(
                        Violation(
                            vendor_id=contract.vendor_id,
                            vendor_name=contract.vendor_name,
                            contract_id=contract.id,
                            sla_term_name=f"anomaly_{metric}",
                            metric=metric,
                            actual_value=round(event.value, 4),
                            threshold=0.0,
                            operator="anomaly",
                            period="event",
                            detected_at=datetime.utcnow(),
                            severity=Severity.WARNING,
                            period_start=event.timestamp,
                            period_end=event.timestamp,
                            detection_method="anomaly",
                            notes=(
                                f"Isolation Forest flagged value={event.value:.2f} "
                                f"as anomalous for metric '{metric}'."
                            ),
                        )
                    )
                    logger.warning(
                        "ANOMALY detected: vendor=%s metric=%s value=%.2f",
                        contract.vendor_id,
                        metric,
                        event.value,
                    )

        return violations

    def get_history_size(self, vendor_id: str, metric: str) -> int:
        return len(self._history.get(vendor_id, {}).get(metric, []))
