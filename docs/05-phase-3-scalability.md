# Phase 3: Scalable Reporting and Advanced Automation

## Objective
Elevate the platform from a single-run utility to a robust, scalable QA tool capable of testing complex forms, retaining historical data, and analyzing cross-field dependencies by integrating with the team's Snowflake analytics ecosystem.

## Scope

### In Scope
- **Multi-Field Combinatorial Testing:**
  - Implementation of a Pairwise (All-Pairs) algorithm to test field interactions efficiently.
- **Multi-Page Workflows (Extensibility):**
  - Expanding the architecture to support stateful, multi-page form workflows (e.g., Wizards, checkout flows).
  - Preserving session state across pages and intelligently chaining AI inferences from step to step.
- **Data Persistence & Analytics:**
  - Transition from local JSON files to Snowflake for long-term historical storage and trend analysis.
  - Implementation of a **Snowflake Adapter/Export Layer** that flattens the Pydantic models into normalized formats for ingestion.
  - Implementation of data ingestion pipelines (e.g., Snowflake Connector for Python) for run results.
- **Run History & Metrics:**
  - Implementation of a summary dashboard powered by Snowflake queries to compare results across multiple runs and detect regression trends.
- **Advanced Exporting:**
  - Structured CSV and machine-readable JSON exports for CI/CD ingestion (JUnit-style XML if required).
- **Automation Resilience:**
  - Self-healing locator strategies (using multiple attributes like name, label, and position).
  - Configurable timeouts and retry logic for flakey network conditions.
  - Cross-browser support (Chromium, Firefox, Webkit) via Playwright.

### Out of Scope
- Fully automated CAPTCHA or multi-factor authentication (MFA) bypassing.
- Native mobile app automation (restricted to Web/Mobile Web).
- Performance/Load testing features.

## Files to Create or Modify
- `src/veriform/analytics/`: New module for Snowflake connection and data ingestion logic.
- `src/veriform/workflow/`: New module for stateful multi-page workflow management.
- `src/veriform/generator/pairwise.py`: Implementation of the All-Pairs algorithm.
- `src/veriform/executor/locators.py`: Resilient locator logic for self-healing.
- `src/veriform/api/`: FastAPI routes for dashboard data (querying Snowflake).
- `src/veriform/reporter/exports.py`: Logic for CSV and XML export formats.

## Acceptance Criteria
- **AC1: Pairwise Generation:** Given a form with 10 fields, the system must generate a test suite that covers all 2-way combinations of field values, significantly smaller than the full Cartesian product.
- **AC2: Historical Tracking:** Users must be able to view and compare the results of the current run against the previous runs via the Snowflake-backed dashboard.
- **AC3: Self-Healing:** If a field's `id` changes but its `name` and `label` remain the same, the execution module must still successfully locate and fill the field.
- **AC4: CI Integration:** The system must produce an export file (e.g., JSON or JUnit XML) that can be parsed by a standard CI pipeline (Jenkins/GitHub Actions).

## Testing Strategy
- Snowflake integration tests using a development schema.
- End-to-end tests for the entire pipeline including history reporting from Snowflake.
- Pairwise generation logic thoroughly tested with properties and edge cases.

## Done Means Done Checklist
- [ ] Snowflake table schema is defined and successfully stores `RunSummary` data.
- [ ] Pairwise algorithm is verified against a known dataset for coverage correctness.
- [ ] Self-healing logic successfully handles at least 3 common DOM mutation scenarios.
- [ ] Export module produces valid CSV and XML files.
- [ ] Multi-browser Pytest suite passes on Chromium, Firefox, and Webkit.
- [ ] Documentation includes setup instructions for the Snowflake integration.
