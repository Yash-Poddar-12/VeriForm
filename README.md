# VeriForm

**Deterministic URL-based form testing platform**

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
| Analytics *(Phase 3)* | Snowflake |

---

## Project Structure

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

## Quick Start

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

## Phase Roadmap

| Phase | Status | Description |
|---|---|---|
| Phase 1 | 🔨 In Progress | Core MVP – detection, generation, execution, reporting |
| Phase 2 | ⏳ Planned | Multi-type fields, fuzzing, error message capture |
| Phase 3 | ⏳ Planned | Pairwise testing, Snowflake analytics, CI exports |

---

## Docs

See [`docs/`](docs/) for full architecture and phase specifications.
