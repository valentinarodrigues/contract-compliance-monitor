# Contract Compliance Monitor

AI-driven system that automatically monitors vendor usage logs against SLA contract terms, detects violations in real time, and surfaces them through a web dashboard and configurable alerts.

## Features

- **Plug-and-play LLM parsing** — swap between Claude (Anthropic), OpenAI-compatible APIs (LibertyGPT, Azure, etc.), or a mock parser via a single env var
- **Plug-and-play log sources** — simulated data, local JSON files, AWS CloudWatch, or Datadog — switch with one env var
- **Dual detection engine** — rule-based threshold checking + Isolation Forest anomaly detection
- **Web dashboard** — FastAPI + Jinja2 UI with vendor overview, violation explorer, and per-vendor compliance reports
- **Multi-channel alerting** — console, Slack webhook, or SMTP email
- **Audit-ready reports** — JSON and text compliance reports per vendor

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              Log Ingestion Layer             │
│  Simulated | Local File | CloudWatch | DD   │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         Contract Parsing (LLM)               │
│  Mock | Anthropic Claude | OpenAI-compat.    │
│  → Extracts SLA terms as structured rules    │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         Compliance Monitoring Engine         │
│  Rule Engine: threshold checks per period   │
│  Anomaly Detector: Isolation Forest (sklearn)│
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│        Alerting & Reporting Layer            │
│  Console | Slack | Email | JSON Reports      │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│           Web Dashboard (FastAPI)            │
│  / Dashboard  /violations  /report/{vendor}  │
└─────────────────────────────────────────────┘
```

### Project Structure

```
contract-compliance-monitor/
├── config/
│   └── settings.py              # All config & feature flags (env-driven)
├── src/
│   ├── models.py                # Core data models
│   ├── ingestion/
│   │   ├── base.py              # Abstract log source interface
│   │   ├── simulated.py         # Synthetic data generator
│   │   ├── local_file.py        # JSON file reader
│   │   ├── cloudwatch.py        # AWS CloudWatch adapter
│   │   ├── datadog_source.py    # Datadog Logs API adapter
│   │   └── factory.py           # Creates source from LOG_SOURCE env var
│   ├── parsers/
│   │   ├── base.py              # Abstract LLM parser + shared system prompt
│   │   ├── mock_parser.py       # Hardcoded SLA terms (no API key needed)
│   │   ├── anthropic_parser.py  # Claude via Anthropic API
│   │   ├── openai_parser.py     # Any OpenAI-compatible endpoint
│   │   └── factory.py           # Creates parser from LLM_PROVIDER env var
│   ├── monitoring/
│   │   ├── rule_engine.py       # Time-bucketed SLA threshold checks
│   │   ├── anomaly_detector.py  # Isolation Forest on usage patterns
│   │   └── compliance_monitor.py # Orchestrates the full pipeline
│   ├── alerting/
│   │   ├── alert_manager.py     # Dispatches alerts to configured channels
│   │   └── report_generator.py  # Compliance report builder
│   └── dashboard/
│       ├── app.py               # FastAPI routes
│       └── templates/           # Jinja2 HTML templates
├── data/
│   ├── sample_contracts/        # Vendor contract text files
│   └── sample_logs/             # Sample JSON log files
├── main.py                      # CLI entry point
├── requirements.txt
└── .env.example
```

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/valentinarodrigues/contract-compliance-monitor
cd contract-compliance-monitor

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — defaults work out of the box with simulated data and mock LLM
```

### 3. Run

```bash
# One-shot monitoring cycle (simulated logs + mock SLA parsing, no API keys needed)
python main.py monitor

# Continuous polling loop
python main.py monitor --watch

# Web dashboard at http://localhost:8000
python main.py dashboard

# Generate a compliance report for a vendor
python main.py report vendor_a

# Parse a contract file and print extracted SLA terms
python main.py parse data/sample_contracts/vendor_a.txt

# Show system status
python main.py status
```

---

## Configuration

All settings are controlled by environment variables (`.env` file or shell exports).

### Feature Flags

| Variable | Default | Options | Description |
|---|---|---|---|
| `LLM_PROVIDER` | `mock` | `mock` \| `anthropic` \| `openai` | LLM used for contract parsing |
| `LOG_SOURCE` | `simulated` | `simulated` \| `local_file` \| `cloudwatch` \| `datadog` | Log ingestion source |
| `ALERT_CHANNELS` | `console` | `console,slack,email` | Comma-separated alert channels |

### LLM Providers

**Mock** (default, no API key required)
```env
LLM_PROVIDER=mock
```
Returns hardcoded SLA terms per vendor. Good for demos and CI.

**Anthropic Claude**
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6   # optional
```

**OpenAI / LibertyGPT / Azure / Ollama**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1   # change for LibertyGPT/Azure/Ollama
OPENAI_MODEL=gpt-4o
```

### Log Sources

**Simulated** (default)
```env
LOG_SOURCE=simulated
```
Generates realistic synthetic logs with random SLA violations injected at ~8% frequency.

**Local JSON files**
```env
LOG_SOURCE=local_file
LOCAL_LOG_DIR=data/sample_logs
```
Reads `{vendor_id}_logs.json` files from the specified directory.

Expected file format:
```json
[
  {
    "timestamp": "2026-03-13T10:00:00",
    "vendor_id": "vendor_a",
    "metric": "api_calls_per_hour",
    "value": 9500,
    "metadata": {}
  }
]
```

**AWS CloudWatch**
```env
LOG_SOURCE=cloudwatch
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
CLOUDWATCH_REGION=us-east-1
CLOUDWATCH_LOG_GROUP=/contract-compliance/logs
```
Log events must be JSON-encoded with `vendor_id`, `metric`, and `value` fields.

**Datadog**
```env
LOG_SOURCE=datadog
DATADOG_API_KEY=...
DATADOG_APP_KEY=...
DATADOG_SITE=datadoghq.com
```
Queries the Datadog Logs API filtered by `@vendor_id` tag.

### Alerting

```env
ALERT_CHANNELS=console,slack,email

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@company.com
SMTP_PASS=...
ALERT_EMAIL_TO=compliance-team@company.com
```

---

## Adding a New Vendor

1. **Add a contract file** at `data/sample_contracts/{vendor_id}.txt`

2. **Add log data** (if using `local_file`) at `data/sample_logs/{vendor_id}_logs.json`

3. The system auto-discovers both on startup — no code changes needed.

---

## Adding a New Log Source

Implement `BaseLogSource` in `src/ingestion/`:

```python
from src.ingestion.base import BaseLogSource
from src.models import LogEvent

class MyLogSource(BaseLogSource):
    def get_vendor_ids(self) -> list[str]:
        return ["vendor_a", "vendor_b"]

    def fetch_logs(self, vendor_id, start_time, end_time) -> list[LogEvent]:
        # fetch and return LogEvent objects
        ...
```

Register it in `src/ingestion/factory.py`:

```python
if provider == "my_source":
    from src.ingestion.my_source import MyLogSource
    return MyLogSource()
```

Set `LOG_SOURCE=my_source` in your `.env`.

---

## Adding a New LLM Provider

Implement `BaseLLMParser` in `src/parsers/`:

```python
from src.parsers.base import BaseLLMParser, EXTRACTION_SYSTEM_PROMPT
from src.models import SLATerm

class MyLLMParser(BaseLLMParser):
    def extract_sla_terms(self, contract_text: str) -> list[SLATerm]:
        # call your LLM, parse response, return SLATerm list
        ...
```

Register it in `src/parsers/factory.py` and set `LLM_PROVIDER=my_llm`.

---

## API Reference

The dashboard exposes a JSON API alongside the HTML UI:

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/status` | System health and violation counts |
| `GET` | `/api/vendors` | All monitored vendors with SLA terms |
| `GET` | `/api/violations` | All violations (filterable by `vendor_id`, `severity`, `resolved`) |
| `GET` | `/api/report/{vendor_id}` | Compliance report as JSON |
| `POST` | `/api/violations/{id}/resolve` | Mark a violation as resolved |

Interactive docs available at `http://localhost:8000/docs` (Swagger UI).

---

## Detection Methods

### Rule-Based (threshold checking)

For each SLA term, logs are grouped into time buckets matching the term's period (`per_hour`, `per_day`, etc.). The worst-case value in each bucket is compared against the threshold:

- `<=` / `<` terms: uses the **max** value in the bucket
- `>=` / `>` terms: uses the **min** value in the bucket

A `Violation` is emitted for every bucket that breaches.

### Anomaly Detection (Isolation Forest)

An Isolation Forest model is trained per vendor/metric pair once at least 20 samples have been collected. New events are scored; any event flagged as an outlier (`score == -1`) produces an anomaly `Violation`. This catches gradual drift and unusual patterns before they cross explicit thresholds.

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Web framework | FastAPI + Jinja2 |
| ML / Anomaly detection | scikit-learn (Isolation Forest) |
| LLM APIs | Anthropic SDK, OpenAI SDK |
| Log sources | boto3 (CloudWatch), datadog-api-client |
| Alerting | Slack webhooks, SMTP |
| Frontend | TailwindCSS CDN + Alpine.js |

---

## Proposed Tech Stack Alignment

| From Proposal | Implementation |
|---|---|
| Python | Python 3.10+ throughout |
| LibertyGPT | OpenAI-compatible adapter (`OPENAI_BASE_URL`) |
| Scikit-learn | Isolation Forest anomaly detection |
| AWS CloudWatch | `cloudwatch.py` adapter |
| Datadog | `datadog_source.py` adapter |
| LLMs for log interpretation | Contract parser layer (Anthropic / OpenAI) |
| Anomaly detection models | `anomaly_detector.py` (sklearn IsolationForest) |

---

## License

MIT
