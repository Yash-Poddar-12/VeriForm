# VeriForm Repository Audit and Learning Guide

## Table of Contents

1. Project Overview
2. Repository Structure
3. Entrypoints & Execution Flow
4. What Is Completed
5. What Is Left To Build
6. Exact File Reading Order
7. Major Module Explanations
8. Testing Analysis
9. Refactoring Analysis
10. Teaching Mode
11. High Priority Fixes
12. Best Next Learning Steps
13. Safest Workflow for Changes

---

# 1. PROJECT OVERVIEW

VeriForm is a Python 3.12 form-testing engine. Given a URL, it loads a page with Playwright, detects form controls, infers field semantics, generates deterministic candidate values, executes those candidates through the form, analyzes observed outcomes, and writes JSON/HTML reports.

Core problem: reduce manual QA effort for web form validation by automatically probing boundaries, invalid formats, required fields, and suspicious payloads.

Current architecture is a linear pipeline centered on:

`src/veriform/orchestrator/orchestrator.py`

Pipeline:

```text
FastAPI route -> orchestrator -> detector -> AI/deterministic inference -> constraint merge -> generator/planner -> executor -> analyzer -> reporter
```

## Tech Stack

- Python 3.12+
- FastAPI / Uvicorn
- Playwright
- Pydantic v2
- Jinja2
- Pytest / pytest-asyncio
- Snowflake planned only

## Design Philosophy

- deterministic-first
- AI inference as assistive metadata, not truth
- modular pipeline boundaries
- local reports first, Snowflake later
- bounded generation to avoid combinatorial explosion

## Important Workflows

- API health: `GET /health`
- API run: `POST /runs/`
- direct orchestration: `run_single_page(target_url)`
- test harness: `FakePage in fake_playwright.py`

---

# 2. REPOSITORY STRUCTURE

## Important Tree

```text
VeriForm/
├── pyproject.toml
├── README.md
├── .env.example
├── fake_playwright.py
├── templates/
│   └── report.html.j2
├── docs/
│   ├── 00-project-vision.md
│   ├── 01-requirements.md
│   ├── 02-architecture.md
│   ├── 03-phase-1-mvp.md
│   ├── 04-phase-2-enhancements.md
│   ├── 05-phase-3-scalability.md
│   ├── 06-test-plan.md
│   ├── 07-api-and-data-model.md
│   ├── 08-python-stack-decision.md
│   ├── structured-constraint-layer.md
│   └── url_based_form_test_automation_spec.md
├── src/veriform/
│   ├── api/
│   ├── orchestrator/
│   ├── detector/
│   ├── ai_inference/
│   ├── constraints/
│   ├── constraint_ir/
│   ├── generator/
│   ├── executor/
│   ├── analyzer/
│   ├── reporter/
│   ├── models/
│   ├── config/
│   ├── utils/
│   └── analytics/
└── tests/
```

## Key Responsibilities

- `pyproject.toml`: package metadata, dependencies, pytest config. Infrastructure.
- `README.md`: quick-start and roadmap. Docs.
- `.env.example`: runtime config template. Config.
- `src/veriform/models/schemas.py`: core Pydantic contracts. Core logic.
- `src/veriform/api/app.py`, `src/veriform/api/routes/runs.py`: FastAPI surface. API.
- `src/veriform/orchestrator/orchestrator.py`: lifecycle coordinator. Core orchestration.
- `src/veriform/detector/detector.py`: browser DOM extraction. Core logic.
- `src/veriform/ai_inference`: deterministic semantic classifier plus provider protocols. Helper/core.
- `src/veriform/constraints`: inferred-constraint merge, feedback adjustment, dependency graph, format synthesis. Core/helper.
- `src/veriform/constraint_ir`: early structured constraint model. Experimental/incomplete.
- `src/veriform/generator`: candidate generation, ranking, bounded planning, test-case mapping. Core logic.
- `src/veriform/executor/executor.py`: Playwright interaction. Core but incomplete for non-text controls.
- `src/veriform/analyzer/analyzer.py`: pass/fail classification. Core.
- `src/veriform/reporter/reporter.py`: JSON/HTML output. Core/helper.
- `src/veriform/analytics/__init__.py`: Snowflake placeholder. Future/deprecated-for-now.
- `tests`: unit/integration coverage using FakePage. Tests.

---

# 3. ENTRYPOINTS & EXECUTION FLOW

## Actual Entrypoints

- API app object: `veriform.api.app:app`
- Health route: `health()`
- Run route: `create_run(payload)`
- Orchestration: `run(target_url)` and `run_single_page(target_url, page=None, reports_root=None)`

## API Flow

1. `src/veriform/api/routes/runs.py` `RunRequest` validates `target_url` as `HttpUrl`.
2. `create_run()` logs and calls `await run(str(payload.target_url))`.
3. `src/veriform/orchestrator/orchestrator.py` `run()` delegates to `run_single_page()`.
4. Errors become HTTP 500 via `OrchestratorError`.

## Runtime Flow

1. `run_single_page()` creates `run_id`, UTC timestamp, and `OrchestrationArtifacts`.
2. If no page is injected, `_try_create_managed_page()` imports Playwright and launches configured browser.
3. `page.goto(target_url, timeout=settings.timeout_ms)`.
4. `detect_fields(page, run_id)` extracts controls from `form input`, `form textarea`, `form select`.
5. `classify_fields(fields, InferenceContext(...))` infers semantic type and likely format.
6. `merge_inferred_constraints()` groups/ranks constraints by field.
7. `generate(fields, merged_constraints)` builds candidates, creates a plan, maps candidates to `TestCaseSchema`.
8. `execute(page, test_cases, target_url)` navigates, fills one field, submits, observes URL/error text.
9. `analyze(raw_results, test_cases)` normalizes outcomes and sets pass/fail.
10. `_build_execution_feedback()` groups observed outcomes per field.
11. `apply_feedback_to_constraints()` adjusts confidence.
12. `_build_run_summary()` computes counters.
13. `reporter.generate()` writes `report.json` and `report.html`.

## Validation Flow

- Pydantic schemas enforce expected outcomes, observed outcomes, status, numeric bounds.
- `RunRequest.target_url` uses Pydantic `HttpUrl`.
- `constraint_ir` models enforce immutability, strict typing, and length bounds.
- No runtime validation prevents internal SSRF, unsafe target hosts, or excessive generated browser traffic.

## Parsing Flow

- DOM parsing happens inside the JavaScript string in `detect_fields()`.
- Semantic parsing happens in `parse_semantic_hints()`, which lowercases metadata and tokenizes with regex.
- Pattern interpretation happens in `synthesize_likely_format()` and `_regex_specs()`.

## Test Flow

- Tests use `FakePage` instead of real Playwright for most integration behavior.
- `tests/conftest.py` creates an ASGI `api_client`.
- Current fixture `workspace_tmp_path()` hardcodes `C:\tmp`, which is not portable.

---

# 4. WHAT IS COMPLETED

## Fully Implemented

- Pydantic contracts for fields, constraints, candidates, plans, test cases, results, summaries.
- FastAPI health and run endpoints.
- Single-page orchestration.
- DOM detection for form inputs, textareas, selects, excluding hidden inputs.
- Deterministic semantic classification for common field types.
- Candidate generation for many semantics: email, phone/mobile, account, DOB/date, postal, address, amount, select, boolean, free text.
- Bounded candidate count per field: `MAX_CANDIDATES_PER_FIELD = 12`.
- Bounded global plan: `MAX_PLANNER_COMBINATIONS = 40`.
- Basic Playwright execution for fillable text-like controls.
- Basic validation message scraping.
- JSON/HTML report writing.
- Constraint feedback confidence adjustment.
- Constraint IR base plus length/charset primitives.

## Partially Implemented

- Select/checkbox/radio support: detector/generator know about them, executor still uses `.fill()`.
- Screenshots: only captured on crash, not every failed test.
- AI integration: provider protocols exist, no real provider implementation.
- Pattern learning: confidence delta exists, but no persistent learning or future-run reuse.
- Constraint IR: docs are extensive; implementation only covers enum, immutable base, length/charset.
- API async model: route returns `202` but waits synchronously until run completes.
- Reports: summary/results only in HTML; constraints/feedback are only in JSON.

## TODOs / Placeholders

- `src/veriform/ai_inference/field_classifier.py`: provider conflict resolution.
- `src/veriform/ai_inference/semantic_parser.py`: locale-aware tokenization.
- `src/veriform/ai_inference/provider_interface.py`: locale/session metadata later.
- `src/veriform/constraints/inferred_constraints.py`: conflict resolution and adaptive updates.
- `src/veriform/generator/generator.py`: restore richer category generation.
- `src/veriform/api/routes/runs.py`: background runs and polling.
- `src/veriform/analytics/__init__.py`: Snowflake adapter.
- Empty files:
  - `constraint_ir/models/profile.py`
  - `constraint_ir/models/segments.py`
  - `constraint_ir/adapters/translator.py`

## Technical Debt / Unstable Areas

- Executor only tests one field at a time; required fields other than the target remain empty, causing false rejections.
- Selectors are built with raw `dom_id/name`; quote/CSS escaping issues are possible.
- `detect_fields()` uses `label[for="${element.id}"]` without escaping the ID.
- `date.today()` in candidate generation makes output time-dependent.
- Playwright timeout errors may not be classified as `timeout` because Playwright has its own timeout exception class.
- Generated report paths and screenshots are inconsistent.
- `tests/conftest.py` hardcodes Windows temp path.
- `POST /runs/` can drive Playwright to arbitrary URLs.

---

# 5. WHAT IS LEFT TO BUILD

## Missing Features

- Real background run lifecycle.
- Real persistence for run states and report metadata.
- Multi-field valid baseline filling before testing one field.
- Pairwise/multi-field combination testing.
- Select option extraction and execution.
- Checkbox/radio execution behavior.
- File upload/date picker edge handling.
- Robust SPA/dynamic validation waits.
- CSV/JUnit/XML exports.
- Snowflake adapter.
- Dashboard/frontend.

## Missing Validation/Security

- Target URL allowlist/blocklist.
- Private-network SSRF protection.
- Request authentication/rate limiting.
- Browser execution sandbox policy.
- Max fields / max runtime / max reports limits.
- Input selector escaping.
- Safer report path handling.
- No guarantee reports directory cleanup.

## Missing Tests

- Real Playwright integration tests.
- API failure tests.
- SSRF/security tests.
- Dynamic validation timing tests.
- Select/checkbox/radio executor tests.
- Multiple required fields scenario.
- CSS selector escaping.
- Report HTML content beyond file existence.
- Constraint IR profile/segment/translator tests once implemented.

## Production-Readiness Gaps

- No job queue.
- No cancellation.
- No concurrency control.
- No persistent run status.
- No structured JSON logs.
- No metrics/tracing.
- No cleanup policy for reports/screenshots.
- No Docker/CI setup visible.
- No browser-install verification workflow.

---

# 6. EXACT FILE READING ORDER

## Step 1

### Read

- `README.md`
- `pyproject.toml`
- `.env.example`

### Learn

- package purpose
- dependencies
- commands
- runtime knobs

### Why This Matters

This defines how the project is supposed to run before inspecting internals.

---

## Step 2

### Read

- `docs/00-project-vision.md`
- `docs/01-requirements.md`
- `docs/02-architecture.md`

### Learn

- product goal
- architecture boundaries
- phase thinking

### Why This Matters

Lets you distinguish intentional deferrals from bugs.

---

## Step 3

### Read

- `src/veriform/models/schemas.py`

### Learn

- the data contracts every module passes around

### Why This Matters

This is the vocabulary of the whole codebase.

---

## Step 4

### Read

- `src/veriform/api/app.py`
- `src/veriform/api/routes/runs.py`
- `src/veriform/orchestrator/orchestrator.py`

### Learn

- actual entrypoints and lifecycle order

### Why This Matters

The orchestrator explains how modules connect in production.

---

## Step 5

### Read

- `src/veriform/detector/detector.py`
- `src/veriform/ai_inference/semantic_parser.py`
- `src/veriform/ai_inference/field_classifier.py`
- `src/veriform/constraints/structured_synthesis.py`

### Learn

- how DOM metadata becomes semantic hypotheses

### Why This Matters

Detection/inference quality determines all downstream test quality.

---

## Step 6

### Read

- `src/veriform/constraints/inferred_constraints.py`
- `src/veriform/generator/candidate_generator.py`
- `src/veriform/generator/combination_planner.py`
- `src/veriform/generator/generator.py`

### Learn

- how hypotheses become executable cases

### Why This Matters

Most product intelligence currently lives here.

---

## Step 7

### Read

- `src/veriform/executor/executor.py`
- `src/veriform/analyzer/analyzer.py`
- `src/veriform/reporter/reporter.py`
- `templates/report.html.j2`

### Learn

- how test cases become observed results and reports

### Why This Matters

This is where theoretical test generation meets browser reality.

---

## Step 8

### Read

- `fake_playwright.py`
- `tests`

### Learn

- how behavior is currently verified

### Why This Matters

Tests reveal intended contracts and untested gaps.

---

## Step 9

### Read

- `docs/structured-constraint-layer.md`
- `src/veriform/constraint_ir`

### Learn

- planned structured constraint model versus actual implementation

### Why This Matters

This is future architecture, not current runtime truth.

---

# 7. MAJOR MODULE EXPLANATIONS

## src/veriform/models/schemas.py

- Solves cross-module data consistency.
- Main classes:
  - `FieldSchema`
  - `InferredConstraintSchema`
  - `CandidateInputSchema`
  - `CombinationPlanSchema`
  - `TestCaseSchema`
  - `ResultSchema`
  - `RunMetrics`
  - `RunSummarySchema`
- Good: explicit `run_id` propagation and validators.
- Improve: use enums instead of free strings.

## src/veriform/orchestrator/orchestrator.py

- Solves run lifecycle coordination.
- Main functions/classes:
  - `run`
  - `run_single_page`
  - `_try_create_managed_page`
  - `OrchestrationArtifacts`
  - `_build_run_summary`
- Good: linear readable flow.
- Improve: background jobs, dependency injection, better error taxonomy, run status persistence.

## src/veriform/detector/detector.py

- Solves DOM-to-FieldSchema.
- Important:
  - `detect_fields()`
  - `_as_optional_str/int/float`
- Handles labels, aria-describedby, required, length, pattern, min/max.
- Gaps: form-only selection, no option extraction, no CSS escaping.

## src/veriform/ai_inference

- Solves semantic classification without real AI calls.
- Important:
  - `classify_fields()`
  - `_infer_semantic_type()`
  - `_confidence_for()`
  - `parse_semantic_hints()`
  - provider protocols
- Good: deterministic-first provider abstraction.
- Gaps: no provider implementation, no conflict strategy beyond higher confidence.

## src/veriform/constraints

- Solves inferred constraint grouping and format descriptors.
- Important:
  - `merge_inferred_constraints()`
  - `apply_feedback_to_constraints()`
  - `synthesize_likely_format()`
  - `DependencyGraph`
- Good: feedback mechanism exists.
- Gaps: no actual HTML-vs-inference conflict resolution; graph unused.

## src/veriform/generator

- Solves deterministic candidate creation and bounded planning.
- Important:
  - `build_candidate_inputs()`
  - `_semantic_specs()`
  - `_regex_specs()`
  - `_length_specs()`
  - `_numeric_specs()`
  - `_date_specs()`
  - `create_combination_plan()`
  - `generate()`
- Good: broad semantic catalog and caps.
- Gaps: some values are synthetic placeholders, not DOM-aware; date generation is time-dependent; field interactions are absent.

## src/veriform/executor/executor.py

- Solves browser execution.
- Important:
  - `execute()`
  - `_selector_for_test_case()`
  - `_submit_form()`
  - `_extract_validation_message()`
  - `_classify_raw_outcome()`
- Good: simple and testable with fake page.
- Gaps: `.fill()` cannot cover select/checkbox/radio; false negatives when other required fields are empty; weak validation detection.

## src/veriform/analyzer/analyzer.py

- Solves expected-vs-observed status classification.
- Important:
  - `analyze()`
  - `_normalize_outcome()`
- Good: clear normalization.
- Gap: does not infer richer failure reasons.

## src/veriform/reporter/reporter.py

- Solves report output.
- Important:
  - `generate()`
- Good: writes JSON and HTML.
- Gaps: HTML omits constraints/feedback/screenshots; no CSV despite docs.

## src/veriform/constraint_ir

- Solves planned formal constraint representation.
- Implemented:
  - `CharsetCategory`
  - `ImmutableIRModel`
  - `LengthConstraint`
  - `CharsetConstraint`
  - discriminated union
- Empty:
  - profile
  - segments
  - translator
- This is experimental and not integrated into runtime generation.

---

# 8. TESTING ANALYSIS

## Covered

- Schema validation.
- Detector extraction using FakePage.
- Candidate generation for fintech/common semantics.
- Combination planning dedupe, priority, field coverage, global cap.
- Analyzer pass/fail normalization.
- Executor basic accepted/validation-error behavior.
- Reporter file creation.
- Orchestrator smoke/injected fake-page flow.
- API health and run happy path.
- Constraint IR immutability and atomic constraints.

## Weak Areas

- Tests are heavily fake-page based; real Playwright behavior is not verified.
- API `POST /runs/` test does not monkeypatch Playwright.
- `workspace_tmp_path()` hardcodes `C:\tmp`, making tests non-portable.
- No tests for malformed selectors.
- No tests for multiple required fields.
- No tests for select/checkbox/radio execution.
- No tests for real validation messages in modern SPAs.
- No tests for security controls around target URLs.
- No coverage assertion despite docs mentioning >80%.

---

# 9. REFACTORING ANALYSIS

## Tightly Coupled

- `run_single_page()` directly imports and invokes every pipeline stage.
- executor depends on global settings.
- reporter computes template location by relative parent traversal.
- Candidate generation mixes semantic inference fallback, format strategy, safety payloads, and prioritization.

## Bad/Weak Abstractions

- `InferenceInterface` and `CandidatePlanningInterface` protocols exist in orchestrator but are unused.
- `constraint_ir` is documented as a future core layer but disconnected from runtime generation.
- Categories/statuses are strings everywhere.

## Naming Issues

- `ai_inference` currently contains deterministic heuristics, not AI.
- `generate()` exists in both generator and reporter.
- `observed_outcome` supports both legacy and newer status names.

## Underengineering

- No job/run state model.
- No robust locator abstraction.
- No result evidence model beyond screenshot path.
- No URL security policy.

## Overengineering

- Some future-facing protocols and IR docs exceed current implementation.
- `OrchestrationArtifacts.ranked_candidates` exists but is not populated.

## Simplification Opportunities

- Move all status/category/outcome strings to enums.
- Introduce an ExecutionStrategy per control type.
- Split candidate generator into semantic catalogs plus field-attribute generators.
- Make `reporter.generate` accept a complete report payload object.

---

# 10. TEACHING MODE

The central architectural decision is deterministic-first testing. That is correct for this product because form validation is empirical: the browser result is truth, not the classifier. The current classifier should only propose what to try.

The pipeline pattern is industry-standard for test automation systems:

1. extract facts
2. infer hypotheses
3. generate probes
4. execute probes
5. analyze observations
6. report evidence

The major tradeoff is speed versus correctness. Testing one field at a time is simple and cheap, but it breaks on forms where other required fields must be valid. Production systems usually maintain a valid baseline fixture for all fields, then mutate one field per test.

## Beginner Mistakes to Avoid

- Do not add random generation without deterministic seeds.
- Do not trust inferred semantic types as truth.
- Do not add new field types only in the generator; executor must know how to interact with them.
- Do not change Pydantic schemas casually; every module depends on them.
- Do not assume URL navigation equals successful form acceptance for all apps.
- Do not add external AI calls inside the orchestrator; keep providers behind protocols.
- Do not ignore selector escaping.

---

# 11. HIGH PRIORITY FIXES

1. Add target URL safety policy before exposing API beyond local use.
2. Fix executor to fill a valid baseline for all required fields before mutating one field.
3. Add control-type execution strategies for:
   - text
   - select
   - checkbox
   - radio
   - date
   - number
4. Fix test portability and remove `C:\tmp` dependency.
5. Improve `templates/report.html.j2` and `src/veriform/reporter/reporter.py` to display inferred constraints and feedback already present in JSON.

---

# 12. BEST NEXT LEARNING STEPS

1. Trace one fake run through `tests/test_orchestrator.py`.
2. Step through `run_single_page()` linearly.
3. Inspect generated `report.json` structure.
4. Modify one candidate strategy in `candidate_generator.py`.
5. Add one focused test before changing executor behavior.

---

# 13. SAFEST WORKFLOW FOR CHANGES

1. Start from a small failing test.
2. Change one module boundary at a time.
3. Keep schema changes last and explicit.
4. Run targeted tests, then full suite.
5. Inspect generated report output manually.
6. Avoid touching ignored/generated files.

