# VeriForm

> [!WARNING]  
> **Notice:** Active development has moved to **[VeriForm 2.0](veriform_v2/README.md)**.  
> VeriForm 2.0 represents a fundamental architecture pivot to an event-driven, deterministic fuzzing engine. VeriForm 1.0 (this directory) is considered legacy and will be deprecated once VeriForm 2.0 achieves parity.

---

**Deterministic URL-based form testing platform (Legacy V1)**

VeriForm accepts a web form URL, detects its input fields, generates test values deterministically, executes them through browser automation, and produces structured HTML and JSON reports.

---

## Technology Stack

| Layer | Tool |
|---|---|
| Language | Python 3.12+ |
| Browser Automation | Playwright Python |
| Backend / API | FastAPI |
| Data Validation | Pydantic |
| Testing | Pytest |
| Reporting | Jinja2 |

---

## Project Structure (V1)

```
veriform/
├── src/veriform/
│   ├── api/            FastAPI routes
│   ├── orchestrator/   Run lifecycle
│   ├── detector/       DOM inspection
│   ├── generator/      Test value generation
│   ├── executor/       Playwright browser control
│   ├── analyzer/       Result classification
│   ├── reporter/       HTML & JSON report output
│   ├── models/         Pydantic schemas
│   ├── config/         App configuration
│   └── utils/          Shared utilities
├── tests/              Pytest suite
├── templates/          Jinja2 HTML templates
├── reports/            Runtime output (gitignored)
├── docs/               Architecture documentation
└── pyproject.toml
```

---

## Quick Start (V1)

```bash
# 1. Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate          # Windows
source .venv/bin/activate         # macOS/Linux

# 2. Install dependencies (editable)
pip install -e ".[dev]"

# 3. Install Playwright browsers
playwright install chromium

# 4. Copy environment config
copy .env.example .env

# 5. Start the API server
uvicorn veriform.api.app:app --reload

# 6. Run the test suite
pytest
```

---

## Phase Roadmap (Legacy)

| Phase | Status | Description |
|---|---|---|
| Phase 1 | 🔨 Suspended | Core MVP – detection, generation, execution, reporting |
| Phase 2 | ➡️ Migrated | Shifted to VeriForm 2.0 (Deterministic Engine) |
| Phase 3 | ⏳ Planned | Pairwise testing, Snowflake analytics, CI exports |

---

## Docs

See [`docs/`](docs/) for V1 architecture and phase specifications. For the latest architecture blueprints, refer to the `veriform_v2` directory.
