# System Architecture

## Architectural Principles
1. **Deterministic-First Foundation:** The platform relies on deterministic DOM inspection to ground all operations. Deterministic execution must validate all AI hypotheses.
2. **AI as Assistant, Not Truth:** AI should assist inference only (e.g., semantic meaning of fields, likely valid formats). AI should never directly determine truth.
3. **Extensibility:** The architecture MUST remain extensible for future multi-page workflow support, although Phase 1 is restricted to single-page forms.
4. **Modular Design:** Strong boundaries between extraction, inference, generation, execution, and reporting.
5. **Pluggable Architecture:** Designed to easily add new "strategies" for AI inference or test generation.
6. **Snowflake-Ready Data:** Run data models are normalized for future Snowflake ingestion (explicitly deferred to Phase 3).

## Technology Stack
- **Language:** Python 3.12+
- **Backend Orchestration:** FastAPI
- **Browser Automation:** Playwright Python
- **Data Validation & Schemas:** Pydantic
- **Testing:** Pytest
- **Reporting (Phase 1/2):** Jinja2 templates and JSON generators
- **Analytics & Persistence (Phase 3):** Snowflake

## High-Level Execution Flow
```text
┌───────────────────────────────┐
│          User Interface       │
│   (URL entry + run controls)  │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│        Orchestration          │
│   (FastAPI / Run Manager)     │
└───────────────┬───────────────┘
                │
      ┌─────────┴─────────┐
      ▼                   ▼
┌──────────────┐    ┌──────────────┐
│Field Detector│───►│ AI Inference │
│(Deterministic)│    │ (Semantics & │
└──────┬───────┘    │ Constraints) │
       │            └──────┬───────┘
       │                   │
       ▼                   ▼
┌──────────────────────────────────┐
│       Constraints Manager        │
└────────────────┬─────────────────┘
                 │
                 ▼
┌──────────────────────────────────┐
│ Combination Planner & Generator  │
└────────────────┬─────────────────┘
                 │
                 ▼
         ┌──────────────────┐
         │  Test Execution  │
         │(Playwright Async)│
         └───────┬──────────┘
                 │
                 ▼
         ┌──────────────────┐
         │ Result Analyzer  │
         │ (+ Pattern Learner)
         └───────┬──────────┘
                 │
                 ▼
         ┌──────────────────┐
         │ Report Generator │
         │    (Jinja2)      │
         └───────┬──────────┘
                 │
                 ▼
         ┌──────────────────┐
         │ Analytics Ingest │
         │   (Snowflake)    │
         │    (Phase 3)     │
         └──────────────────┘
```

## Python Package Structure
```text
veriform/
├── src/
│   └── veriform/
│       ├── __init__.py
│       ├── api/                # FastAPI routes and server config
│       ├── models/             # Pydantic schemas (FieldSchema, etc.)
│       ├── orchestrator/       # Run lifecycle management
│       ├── detector/           # Playwright DOM inspection
│       ├── ai_inference/       # AI semantic meaning & format inference
│       ├── constraints/        # Manages inferred & explicit field constraints
│       ├── generator/          # Combination planner and test generation
│       ├── executor/           # Playwright browser interactions
│       ├── analyzer/           # Result observation & pattern learning
│       ├── reporter/           # Jinja2 HTML and JSON generation
│       └── analytics/          # Snowflake integration (Phase 3)
├── tests/
│   ├── conftest.py
│   ├── test_detector.py
│   ├── test_generator.py
│   ├── test_executor.py
│   ├── test_analyzer.py
│   └── test_reporter.py
├── templates/                  # Jinja2 HTML report templates
├── pyproject.toml              # Dependencies and build config
└── README.md
```

## Module Breakdown and Boundaries

### 1. Orchestrator Module (`veriform.orchestrator`)
**Responsibility:** The central controller. It receives the test request via FastAPI, initializes the Playwright async browser context, and sequentially invokes the Detector, Generator, Executor, and Reporter. In Phase 3, it optionally triggers the Analytics Ingest.

### 2. Field Detector Module (`veriform.detector`)
**Responsibility:** Interacts with the Playwright page object to parse the DOM deterministically. It identifies all `input`, `textarea`, and `select` elements, extracting standard HTML5 attributes to form a baseline `FieldSchema`.

### 3. AI Inference Module (`veriform.ai_inference`)
**Responsibility:** Takes the detected fields and infers their semantic meaning (e.g., recognizing a generic text field is actually a "social security number" field). It infers likely valid formats and assigns confidence scores to these hypotheses.

### 4. Constraints Manager (`veriform.constraints`)
**Responsibility:** Merges deterministic HTML constraints with AI-inferred constraints. It acts as the source of truth for the properties each field should possess, supporting accepted/rejected pattern learning.

### 5. Test Generator & Combination Planner (`veriform.generator`)
**Responsibility:** Employs a combination planner strategy to reduce unnecessary test combinations while intelligently selecting candidate inputs. It uses the merged constraints to generate highly relevant `TestCaseSchema` payloads.

### 6. Test Execution Module (`veriform.executor`)
**Responsibility:** Drives the browser. It receives the test cases, navigates to the URL, populates the fields via Playwright, and triggers form submission deterministically validating AI hypotheses.

### 7. Result Analyzer Module (`veriform.analyzer`)
**Responsibility:** Compares observed post-submission states against expected outcomes. Feeds accepted/rejected results back to the pattern learning layer to refine future constraint confidence.

### 6. Report Generator Module (`veriform.reporter`)
**Responsibility:** Aggregates the raw test results, schemas, and screenshots into a finalized `RunSummarySchema`. Uses Jinja2 to render HTML reports for immediate local viewing.

### 7. Analytics Module (`veriform.analytics`) - Phase 3
**Responsibility:** Handles long-term persistence and trend analysis by ingesting `RunSummary` data into Snowflake. Provides methods for historical comparison and analytics dashboards.

---

## Module Dependencies

The system follows a strict linear dependency flow managed by the Orchestrator:

1.  **Orchestrator** depends on: `Field Detector`, `AI Inference`, `Constraints Manager`, `Test Generator`, `Test Execution`, `Result Analyzer`, `Report Generator`, and optionally `Analytics`.
2.  **Field Detector** depends on: `Playwright`, `models`.
3.  **AI Inference** depends on: `models` (receives detected schemas).
4.  **Constraints Manager** depends on: `models`, `ai_inference`.
5.  **Test Generator** depends on: `constraints`, `models`.
6.  **Test Execution** depends on: `Playwright`, `models`.
7.  **Result Analyzer** depends on: `Playwright`, `models`, optionally `constraints` for pattern learning.
8.  **Report Generator** depends on: `Jinja2`, `models`.
9.  **Analytics** depends on: `Snowflake Connector`, `models`.

---

## Data Model Flow
`URL` -> [Detector] -> `FieldSchema` -> [Generator] -> `TestCaseSchema` -> [Execution + Analyzer] -> `ResultSchema` -> [Reporter] -> `RunSummary` -> [Analytics]
