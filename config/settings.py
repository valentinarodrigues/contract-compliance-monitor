from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Feature Flags ────────────────────────────────────────────────────────────
# LLM provider for contract parsing: anthropic | openai | mock
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")

# Log source adapter: simulated | local_file | cloudwatch | datadog
LOG_SOURCE = os.getenv("LOG_SOURCE", "simulated")

# ─── Anthropic ────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# ─── OpenAI / OpenAI-compatible (LibertyGPT, Azure, etc.) ────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# ─── AWS CloudWatch ───────────────────────────────────────────────────────────
CLOUDWATCH_REGION = os.getenv("CLOUDWATCH_REGION", "us-east-1")
CLOUDWATCH_LOG_GROUP = os.getenv("CLOUDWATCH_LOG_GROUP", "/contract-compliance/logs")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# ─── Datadog ──────────────────────────────────────────────────────────────────
DATADOG_API_KEY = os.getenv("DATADOG_API_KEY", "")
DATADOG_APP_KEY = os.getenv("DATADOG_APP_KEY", "")
DATADOG_SITE = os.getenv("DATADOG_SITE", "datadoghq.com")

# ─── Local File ───────────────────────────────────────────────────────────────
LOCAL_LOG_DIR = os.getenv("LOCAL_LOG_DIR", "data/sample_logs")

# ─── Monitoring ───────────────────────────────────────────────────────────────
# Fraction of samples expected to be anomalous (0.0–0.5)
ANOMALY_CONTAMINATION = float(os.getenv("ANOMALY_CONTAMINATION", "0.05"))
POLLING_INTERVAL_SECONDS = int(os.getenv("POLLING_INTERVAL_SECONDS", "60"))
# Minimum log samples required before anomaly model activates
MIN_SAMPLES_FOR_ANOMALY = int(os.getenv("MIN_SAMPLES_FOR_ANOMALY", "20"))

# ─── Dashboard ────────────────────────────────────────────────────────────────
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8000"))

# ─── Alerting ─────────────────────────────────────────────────────────────────
# Comma-separated list: console, slack, email
ALERT_CHANNELS = [c.strip() for c in os.getenv("ALERT_CHANNELS", "console").split(",")]
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "compliance-monitor@company.com")
