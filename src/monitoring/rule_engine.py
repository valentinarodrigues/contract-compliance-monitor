from __future__ import annotations
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from src.models import Contract, LogEvent, Period, Severity, Violation

logger = logging.getLogger(__name__)

# Maps Period enum to the timedelta used for aggregation buckets
PERIOD_DELTAS: dict[Period, timedelta] = {
    Period.PER_MINUTE: timedelta(minutes=1),
    Period.PER_HOUR: timedelta(hours=1),
    Period.PER_DAY: timedelta(days=1),
    Period.PER_MONTH: timedelta(days=30),
    Period.ROLLING_24H: timedelta(hours=24),
}


class RuleEngine:
    """
    Checks log events against explicit SLA thresholds in a contract.

    For each SLA term:
      1. Bucket log events by the term's period window
      2. Aggregate (max / min / mean) the metric values in each bucket
      3. Check the aggregate against the threshold
      4. Emit a Violation for every bucket that breaches
    """

    def check(
        self,
        contract: Contract,
        logs: list[LogEvent],
        period_start: datetime,
        period_end: datetime,
    ) -> list[Violation]:
        violations: list[Violation] = []

        # Index logs by metric for fast lookup
        logs_by_metric: dict[str, list[LogEvent]] = defaultdict(list)
        for event in logs:
            logs_by_metric[event.metric].append(event)

        for term in contract.sla_terms:
            metric_logs = logs_by_metric.get(term.metric, [])
            if not metric_logs:
                logger.debug(
                    "No logs found for metric '%s' (vendor=%s)", term.metric, contract.vendor_id
                )
                continue

            delta = PERIOD_DELTAS[term.period]
            buckets = _bucket_logs(metric_logs, delta, period_start, period_end)

            for bucket_start, bucket_events in buckets.items():
                if not bucket_events:
                    continue

                agg_value = _aggregate(bucket_events, term.operator.value)
                bucket_end = bucket_start + delta

                if term.is_violated(agg_value):
                    violations.append(
                        Violation(
                            vendor_id=contract.vendor_id,
                            vendor_name=contract.vendor_name,
                            contract_id=contract.id,
                            sla_term_name=term.name,
                            metric=term.metric,
                            actual_value=round(agg_value, 4),
                            threshold=term.threshold,
                            operator=term.operator.value,
                            period=term.period.value,
                            detected_at=datetime.utcnow(),
                            severity=term.severity,
                            period_start=bucket_start,
                            period_end=bucket_end,
                            detection_method="rule_based",
                            notes=(
                                f"{term.description} "
                                f"Actual={agg_value:.2f}, Threshold={term.operator.value}{term.threshold}"
                            ),
                        )
                    )
                    logger.warning(
                        "VIOLATION [%s] vendor=%s metric=%s actual=%.2f threshold=%s%.2f",
                        term.severity.value.upper(),
                        contract.vendor_id,
                        term.metric,
                        agg_value,
                        term.operator.value,
                        term.threshold,
                    )

        return violations


def _bucket_logs(
    logs: list[LogEvent],
    delta: timedelta,
    period_start: datetime,
    period_end: datetime,
) -> dict[datetime, list[LogEvent]]:
    """Divide logs into fixed-width time buckets."""
    buckets: dict[datetime, list[LogEvent]] = {}

    cursor = period_start
    while cursor < period_end:
        buckets[cursor] = []
        cursor += delta

    for event in logs:
        ts = event.timestamp
        # Find bucket start: floor to delta boundary
        offset = (ts - period_start).total_seconds()
        bucket_idx = int(offset / delta.total_seconds())
        bucket_start = period_start + bucket_idx * delta
        if bucket_start in buckets:
            buckets[bucket_start].append(event)

    return buckets


def _aggregate(events: list[LogEvent], operator: str) -> float:
    """
    Aggregate a list of log events into a single representative value.

    For <= / < (upper-bound caps): use max (worst case)
    For >= / > (lower-bound guarantees): use min (worst case)
    For ==: use mean
    """
    values = [e.value for e in events]
    if operator in ("<=", "<"):
        return max(values)
    if operator in (">=", ">"):
        return min(values)
    return sum(values) / len(values)
