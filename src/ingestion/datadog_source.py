from __future__ import annotations
import logging
from datetime import datetime
from src.ingestion.base import BaseLogSource
from src.models import LogEvent

logger = logging.getLogger(__name__)


class DatadogLogSource(BaseLogSource):
    """
    Fetches log events from Datadog Logs API.

    Requires: datadog-api-client, DATADOG_API_KEY, DATADOG_APP_KEY.
    Logs must be tagged with vendor_id, metric, and value fields.
    """

    def __init__(self, api_key: str, app_key: str, site: str = "datadoghq.com"):
        self.api_key = api_key
        self.app_key = app_key
        self.site = site
        self._logs_api = None

    def _get_api(self):
        if self._logs_api is None:
            try:
                from datadog_api_client import ApiClient, Configuration
                from datadog_api_client.v2.api.logs_api import LogsApi

                config = Configuration()
                config.api_key["apiKeyAuth"] = self.api_key
                config.api_key["appKeyAuth"] = self.app_key
                config.server_variables["site"] = self.site
                self._logs_api = LogsApi(ApiClient(config))
            except ImportError:
                raise RuntimeError(
                    "datadog-api-client is required. Install with: pip install datadog-api-client"
                )
        return self._logs_api

    def get_vendor_ids(self) -> list[str]:
        # Vendor IDs are discovered dynamically from log tags in a real implementation.
        # Return empty here; populate via environment config in production.
        logger.warning(
            "get_vendor_ids is not auto-discovered for Datadog. "
            "Set vendor IDs explicitly in your contract registry."
        )
        return []

    def fetch_logs(
        self, vendor_id: str, start_time: datetime, end_time: datetime
    ) -> list[LogEvent]:
        try:
            from datadog_api_client.v2.model.logs_list_request import LogsListRequest
            from datadog_api_client.v2.model.logs_list_request_page import (
                LogsListRequestPage,
            )
            from datadog_api_client.v2.model.logs_query_filter import LogsQueryFilter
            from datadog_api_client.v2.model.logs_sort import LogsSort

            api = self._get_api()
            query = f"@vendor_id:{vendor_id}"

            request = LogsListRequest(
                filter=LogsQueryFilter(
                    query=query,
                    _from=start_time.isoformat() + "Z",
                    to=end_time.isoformat() + "Z",
                ),
                sort=LogsSort.TIMESTAMP_ASCENDING,
                page=LogsListRequestPage(limit=1000),
            )

            response = api.list_logs(body=request)
            events: list[LogEvent] = []

            for log in response.data or []:
                attrs = log.attributes
                ts = attrs.timestamp.replace(tzinfo=None)
                msg = attrs.attributes or {}
                events.append(
                    LogEvent(
                        timestamp=ts,
                        vendor_id=msg.get("vendor_id", vendor_id),
                        metric=msg.get("metric", "unknown"),
                        value=float(msg.get("value", 0)),
                        metadata=msg.get("metadata", {}),
                    )
                )
            return events

        except Exception as exc:
            logger.error("Datadog fetch_logs failed for %s: %s", vendor_id, exc)
            return []

    def health_check(self) -> bool:
        try:
            self._get_api()
            return True
        except Exception:
            return False
