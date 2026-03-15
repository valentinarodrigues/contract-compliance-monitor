from __future__ import annotations
import json
import logging
from datetime import datetime
from src.ingestion.base import BaseLogSource
from src.models import LogEvent

logger = logging.getLogger(__name__)


class CloudWatchLogSource(BaseLogSource):
    """
    Fetches log events from AWS CloudWatch Logs.

    Requires: boto3, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY (or IAM role).
    Log events must be JSON with fields: vendor_id, metric, value, metadata.
    """

    def __init__(self, log_group: str, region: str = "us-east-1"):
        self.log_group = log_group
        self.region = region
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                from config import settings

                kwargs = {"region_name": self.region}
                if settings.AWS_ACCESS_KEY_ID:
                    kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
                    kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
                self._client = boto3.client("logs", **kwargs)
            except ImportError:
                raise RuntimeError(
                    "boto3 is required for CloudWatch. Install with: pip install boto3"
                )
        return self._client

    def get_vendor_ids(self) -> list[str]:
        client = self._get_client()
        try:
            response = client.describe_log_streams(logGroupName=self.log_group)
            return [s["logStreamName"] for s in response.get("logStreams", [])]
        except Exception as exc:
            logger.error("CloudWatch describe_log_streams failed: %s", exc)
            return []

    def fetch_logs(
        self, vendor_id: str, start_time: datetime, end_time: datetime
    ) -> list[LogEvent]:
        client = self._get_client()
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)

        events: list[LogEvent] = []
        try:
            paginator = client.get_paginator("filter_log_events")
            for page in paginator.paginate(
                logGroupName=self.log_group,
                logStreamNames=[vendor_id],
                startTime=start_ms,
                endTime=end_ms,
            ):
                for event in page.get("events", []):
                    try:
                        record = json.loads(event["message"])
                        ts = datetime.utcfromtimestamp(event["timestamp"] / 1000)
                        events.append(
                            LogEvent(
                                timestamp=ts,
                                vendor_id=record.get("vendor_id", vendor_id),
                                metric=record["metric"],
                                value=float(record["value"]),
                                metadata=record.get("metadata", {}),
                            )
                        )
                    except (json.JSONDecodeError, KeyError) as exc:
                        logger.debug("Skipping malformed log event: %s", exc)
        except Exception as exc:
            logger.error("CloudWatch fetch_logs failed for %s: %s", vendor_id, exc)

        return events

    def health_check(self) -> bool:
        try:
            client = self._get_client()
            client.describe_log_groups(logGroupNamePrefix=self.log_group, limit=1)
            return True
        except Exception:
            return False
