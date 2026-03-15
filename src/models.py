from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class MetricOperator(str, Enum):
    LTE = "<="
    GTE = ">="
    EQ = "=="
    LT = "<"
    GT = ">"


class Period(str, Enum):
    PER_MINUTE = "per_minute"
    PER_HOUR = "per_hour"
    PER_DAY = "per_day"
    PER_MONTH = "per_month"
    ROLLING_24H = "rolling_24h"


@dataclass
class SLATerm:
    name: str
    metric: str
    operator: MetricOperator
    threshold: float
    period: Period
    severity: Severity = Severity.WARNING
    description: str = ""

    def is_violated(self, actual_value: float) -> bool:
        """Returns True if the actual value violates this SLA term."""
        checks = {
            MetricOperator.LTE: actual_value > self.threshold,
            MetricOperator.GTE: actual_value < self.threshold,
            MetricOperator.EQ: actual_value != self.threshold,
            MetricOperator.LT: actual_value >= self.threshold,
            MetricOperator.GT: actual_value <= self.threshold,
        }
        return checks[self.operator]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "metric": self.metric,
            "operator": self.operator.value,
            "threshold": self.threshold,
            "period": self.period.value,
            "severity": self.severity.value,
            "description": self.description,
        }


@dataclass
class Contract:
    id: str
    vendor_id: str
    vendor_name: str
    contract_text: str
    sla_terms: list[SLATerm] = field(default_factory=list)
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "sla_terms": [t.to_dict() for t in self.sla_terms],
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
        }


@dataclass
class LogEvent:
    timestamp: datetime
    vendor_id: str
    metric: str
    value: float
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "vendor_id": self.vendor_id,
            "metric": self.metric,
            "value": self.value,
            "metadata": self.metadata,
        }


@dataclass
class Violation:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vendor_id: str = ""
    vendor_name: str = ""
    contract_id: str = ""
    sla_term_name: str = ""
    metric: str = ""
    actual_value: float = 0.0
    threshold: float = 0.0
    operator: str = ""
    period: str = ""
    detected_at: datetime = field(default_factory=datetime.utcnow)
    severity: Severity = Severity.WARNING
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    detection_method: str = "rule_based"  # rule_based | anomaly
    resolved: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "contract_id": self.contract_id,
            "sla_term_name": self.sla_term_name,
            "metric": self.metric,
            "actual_value": self.actual_value,
            "threshold": self.threshold,
            "operator": self.operator,
            "period": self.period,
            "detected_at": self.detected_at.isoformat(),
            "severity": self.severity.value,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "detection_method": self.detection_method,
            "resolved": self.resolved,
            "notes": self.notes,
        }


@dataclass
class Alert:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    violation_id: str = ""
    sent_at: datetime = field(default_factory=datetime.utcnow)
    channel: str = "console"
    message: str = ""
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "violation_id": self.violation_id,
            "sent_at": self.sent_at.isoformat(),
            "channel": self.channel,
            "message": self.message,
            "success": self.success,
        }


@dataclass
class ComplianceReport:
    vendor_id: str
    vendor_name: str
    period_start: datetime
    period_end: datetime
    total_violations: int = 0
    critical_violations: int = 0
    warning_violations: int = 0
    violations: list[Violation] = field(default_factory=list)
    sla_compliance_rate: float = 100.0
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_violations": self.total_violations,
            "critical_violations": self.critical_violations,
            "warning_violations": self.warning_violations,
            "sla_compliance_rate": round(self.sla_compliance_rate, 2),
            "violations": [v.to_dict() for v in self.violations],
            "generated_at": self.generated_at.isoformat(),
        }
