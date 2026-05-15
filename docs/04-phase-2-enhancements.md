# Phase 2: Intelligent Rule Handling

## Objective
Expand the system's capabilities to handle a wider variety of form inputs, improve the intelligence of the test generation, and increase the accuracy of result classification.

## Scope

### In Scope
- Support for additional field types: `email`, `password`, `number`, `date`, `select` dropdowns.
- Advanced Rule Inference & Pattern Learning:
  - Extracting constraints from localized labels or descriptive text near inputs.
  - Detecting client-side vs. server-side validation differences.
  - Accepted/Rejected Pattern Learning: Feeding execution results back into the Constraints Manager to refine confidence scores and adjust future hypotheses.
- Dynamic Combination Planning Strategy:
  - Expanding the combination planner to use learned patterns to prune the combinatorial space dynamically.
  - Format-specific generation (e.g., malformed email structures, security fuzzing payloads).
- Enhanced Result Classification:
  - Scraping specific validation error message strings from the DOM.
  - Detecting toast notifications and dynamic status changes.
- Deduplication of test vectors to optimize execution time using the combination planner.

### Out of Scope
- Multi-field combinatorial testing (pairwise).
- Automated multi-page workflow navigation (e.g., "Step 2" of a wizard).
- User authentication/session persistence for the testing tool.
- Integration with external CI/CD pipelines (deferred to Phase 3).

## Files to Create or Modify
- `src/veriform/detector/detector.py`: Update to detect `select`, `number`, and `date` elements.
- `src/veriform/generator/generator.py`: Implement logic for email/number/fuzz generation.
- `src/veriform/executor/executor.py`: Add support for interacting with dropdowns and date pickers.
- `src/veriform/analyzer/analyzer.py`: Add logic to capture error message text from the DOM.
- `src/veriform/reporter/reporter.py`: Update Jinja2 HTML template to show detailed error messages and discovered constraints.

## Acceptance Criteria
- **AC1: Multi-Type Detection:** The system must detect and classify `select`, `email`, `password`, and `number` fields with 90% accuracy on standard forms.
- **AC2: Intelligent Data Generation:** For an `email` field, the generator must produce at least 3 invalid formats (missing @, invalid TLD, trailing dots) using the combination planner.
- **AC3: Error Message Capture:** The Analyzer must be able to identify and extract the text content of validation error messages (e.g., "Please enter a valid phone number").
- **AC4: Performance Optimization:** The combination planner must deduplicate identical test cases generated for different fields to reduce redundant form submissions.
- **AC5: Pattern Learning:** The system must demonstrate adjusting a constraint's confidence score based on the observed "accepted" or "rejected" outcome of a prior test case.

## Testing Strategy
- Add parameterized tests using `pytest.mark.parametrize` for the new data generation strategies.
- Add integration tests verifying correct handling of complex field types with Playwright.

## Done Means Done Checklist
- [ ] Field detector supports all 6 target input types (`text`, `email`, `number`, `password`, `textarea`, `select`).
- [ ] Test generator includes a security fuzzing dictionary (SQLi, XSS).
- [ ] Executor handles dropdown selection and date input interactions.
- [ ] Result report displays the exact validation error message captured for failed tests.
- [ ] Coverage tracking prevents running duplicate test cases.
- [ ] Pytest suite for new generation strategies (email, number) passes.
