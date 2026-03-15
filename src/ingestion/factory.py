from __future__ import annotations
from src.ingestion.base import BaseLogSource


def create_log_source(provider: str | None = None) -> BaseLogSource:
    """
    Factory that returns the appropriate log source adapter.

    provider values (overrides LOG_SOURCE env var):
      simulated   – synthetic data, no external dependencies
      local_file  – JSON files from LOCAL_LOG_DIR
      cloudwatch  – AWS CloudWatch Logs
      datadog     – Datadog Logs API
    """
    from config import settings

    provider = (provider or settings.LOG_SOURCE).lower()

    if provider == "simulated":
        from src.ingestion.simulated import SimulatedLogSource
        return SimulatedLogSource()

    if provider == "local_file":
        from src.ingestion.local_file import LocalFileLogSource
        return LocalFileLogSource(log_dir=settings.LOCAL_LOG_DIR)

    if provider == "cloudwatch":
        from src.ingestion.cloudwatch import CloudWatchLogSource
        return CloudWatchLogSource(
            log_group=settings.CLOUDWATCH_LOG_GROUP,
            region=settings.CLOUDWATCH_REGION,
        )

    if provider == "datadog":
        from src.ingestion.datadog_source import DatadogLogSource
        return DatadogLogSource(
            api_key=settings.DATADOG_API_KEY,
            app_key=settings.DATADOG_APP_KEY,
            site=settings.DATADOG_SITE,
        )

    raise ValueError(
        f"Unknown log source provider '{provider}'. "
        "Choose: simulated | local_file | cloudwatch | datadog"
    )
