# Phase 1: Core MVP

## Objective
Establish the foundational end-to-end pipeline for the AI-assisted intelligent form exploration platform. The system must accept a single-page form URL, detect fields deterministically, use lightweight AI to infer semantic meaning and likely valid formats, execute tests to validate hypotheses, and generate a report.

## Scope

### In Scope
- Single-page forms only.
- URL input and page loading using Playwright Python.
- Deterministic detection of standard form fields.
- Lightweight AI Inference:
  - Infer semantic meaning of fields (e.g., "phone number", "SSN").
  - Infer likely valid formats (initial constraint hypothesis).
  - Assign confidence scores to inferred constraints.
- Constraint Management:
  - Merging deterministic attributes with inferred constraints.
- Basic Combination Planner & Test Generation:
  - Generating intelligent candidate inputs based on inferred constraints.
  - Reducing unnecessary combinations to keep the footprint lightweight.
- Deterministic execution of generated tests to validate AI hypotheses.
- Basic failure classification (accepted vs. rejected).
- Report generation capturing test results and validated hypotheses.

### Out of Scope
- Multi-page workflows (explicitly deferred to Phase 3).
- Complex multi-field combinatorial interactions (pairwise).
- Automated accepted/rejected pattern learning (deferred to Phase 2).
- Snowflake Analytics (deferred to Phase 3).
- Handling of dynamic/AJAX-heavy forms requiring complex wait strategies.

## Files to Create or Modify
- `src/veriform/models/schemas.py`: Update `FieldSchema`, `TestCaseSchema`, and introduce inferred constraint schemas with confidence scores.
- `src/veriform/orchestrator/orchestrator.py`: Implement main lifecycle logic.
- `src/veriform/detector/detector.py`: Deterministic DOM inspection logic.
- `src/veriform/ai_inference/inference.py`: New module for lightweight semantic inference.
- `src/veriform/constraints/manager.py`: New module to hold constraint hypotheses.
- `src/veriform/generator/generator.py`: Basic combination planning and test generation logic.
- `src/veriform/executor/executor.py`: Form filling and submission logic.
- `src/veriform/analyzer/analyzer.py`: Post-submission state analysis.
- `src/veriform/reporter/reporter.py`: JSON/HTML file generation using Jinja2.

## Acceptance Criteria
- **AC1: Field Detection:** Given a URL with a standard `<form>` containing text inputs, the system must accurately extract the `name`, `id`, and any `maxlength` attributes for all fields into Pydantic models.
- **AC2: Data Generation:** For a field with `maxlength="10"`, the generator must produce exactly three boundary test cases: length 9, 10, and 11.
- **AC3: Execution Flow:** The system must navigate to the URL, fill the form, and trigger submission without manual intervention for each generated test case.
- **AC4: Outcome Capture:** The system must detect a "rejected" state if the page shows a validation error or stays on the same URL with an error message, and "accepted" if it navigates to a success page.
- **AC5: Report Generation:** A final `report.html` and `report.json` must be saved to the `results/` directory containing all execution outcomes and screenshots.

## Testing Strategy
- Unit and integration testing will be conducted using `pytest`.
- `pytest-asyncio` will be used for testing Playwright-based asynchronous flows.
- Mocking will be used extensively in generator tests to ensure deterministic output.

## Done Means Done Checklist
- [ ] Field detection logic identifies 100% of standard text inputs on a test page.
- [ ] Test generator produces all 7 required test categories (Empty, Short, Boundary, etc.).
- [ ] Executor successfully submits a form using Playwright Python.
- [ ] Analyzer correctly distinguishes between a successful redirect and a validation error.
- [ ] Screenshots are saved for every failed test case.
- [ ] Final HTML report displays a summary table with Pass/Fail counts.
- [ ] Pytest suite for `generator.py` and `detector.py` pass with >80% coverage.
