# URL-Based Form Test Automation Platform

## 1. Project Overview

This project is a browser-based testing tool that accepts a website URL containing one or more forms, automatically detects text/input fields, generates a wide range of test values for each field, submits the form through browser automation, observes whether each input is accepted or rejected, and produces a structured report of the results.

The core value of the product is to reduce manual form-testing effort by automatically discovering input constraints such as valid/invalid value ranges, boundary lengths, format restrictions, and field-specific acceptance rules.

---

## 2. Problem Statement

Manual form testing is repetitive and time-consuming. A tester typically needs to inspect each input field and try many combinations of values to determine:

- what the field accepts,
- what the field rejects,
- the minimum and maximum valid length,
- whether special characters are allowed,
- whether invalid formats are blocked,
- whether validation is client-side or server-side.

The proposed platform automates this process by taking a URL and generating a report that summarizes the observed behavior of the form.

---

## 3. Primary Use Case

**Input:** A URL of a website page containing one or more forms.

**Output:**
- list of detected fields,
- generated test cases for each field,
- execution results for each test case,
- screenshots or logs for failures,
- a final report showing accepted/rejected values and observed constraints.

Example:

- Field: `phone number`
- Values tested: `123`, `1234567890`, `12345678901`, `abcd`, special characters
- Result: accepted/rejected for each case
- Observed rule: accepted only 10 digits

---

## 4. Project Goal

Build an MVP system that can:

1. Accept a form URL.
2. Load the page in a browser.
3. Detect form fields automatically.
4. Generate intelligent test cases for each field.
5. Execute the test cases using browser automation.
6. Collect results and evidence.
7. Generate a readable report.

---

## 5. Scope

### In Scope
- Public or internal web pages with standard forms.
- Text inputs, email inputs, number inputs, textarea, password, select dropdowns.
- Single-step form testing in Phase 1.
- Multiple field handling in later phases.
- Boundary, invalid, and fuzz-style input generation.
- Result collection and reporting.

### Out of Scope for MVP
- CAPTCHA solving.
- OTP handling.
- Deep login/session automation.
- Highly dynamic multi-step flows.
- Native mobile apps.
- PDF form testing.
- File upload testing in initial phases.

---

## 6. Key Functional Requirements

### FR1: URL Input
The system shall accept a URL from the user and open it in a browser automation context.

### FR2: Field Detection
The system shall detect input fields present on the page.

### FR3: Field Classification
The system shall classify fields into types such as:
- text
- number
- email
- password
- textarea
- select

### FR4: Test Case Generation
The system shall generate valid, invalid, boundary, and fuzz test cases for each field.

### FR5: Test Execution
The system shall fill inputs, submit the form, and observe results.

### FR6: Result Classification
The system shall classify outcomes as:
- accepted
- rejected
- validation error shown
- unexpected behavior
- crash/failure

### FR7: Evidence Capture
The system shall store:
- input value,
- field name,
- test result,
- screenshots for failures,
- errors or logs.

### FR8: Report Generation
The system shall generate a report summarizing:
- test cases executed,
- pass/fail status,
- accepted value ranges,
- observed validation behavior.

---

## 7. Non-Functional Requirements

### NFR1: Reliability
Test execution should be repeatable and consistent.

### NFR2: Extensibility
The architecture should support adding new field types and new test strategies later.

### NFR3: Maintainability
Modules should be independent and easy to modify.

### NFR4: Observability
All important actions should be logged for debugging and audit.

### NFR5: Usability
The final report should be understandable by testers and non-technical users.

### NFR6: Performance
A normal test run should complete in reasonable time for small to medium forms.

---

## 8. Recommended Tech Stack

### Frontend
- React or Next.js for dashboard/UI

### Backend
- Python FastAPI or Node.js Express

### Browser Automation
- Playwright

### Test Data Generation
- Custom generator logic
- Optional: Hypothesis (Python) later

### Storage
- JSON files for MVP
- PostgreSQL later if persistence is required

### Reporting
- HTML report for human viewing
- JSON/CSV export for machine readability

---

## 9. System Architecture

```text
┌───────────────────────────────┐
│          User Interface       │
│   URL entry + run controls    │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│        Orchestration          │
│  Manages run lifecycle        │
└───────────────┬───────────────┘
                │
     ┌──────────┴──────────┐
     ▼                     ▼
┌───────────────┐   ┌──────────────────┐
│ Field Detector │   │ Test Generator   │
└──────┬────────┘   └───────┬──────────┘
       │                    │
       └────────┬───────────┘
                ▼
        ┌──────────────────┐
        │ Test Execution    │
        │ Playwright Runner  │
        └───────┬──────────┘
                │
                ▼
        ┌──────────────────┐
        │ Result Analyzer  │
        └───────┬──────────┘
                │
                ▼
        ┌──────────────────┐
        │ Report Generator │
        └──────────────────┘
```

---

## 10. Module Breakdown

### 10.1 UI Module
Responsibilities:
- accept URL input,
- start and stop test run,
- display live status,
- show final report.

### 10.2 Orchestration Module
Responsibilities:
- manage test run lifecycle,
- coordinate field detection, generation, execution, and reporting,
- handle errors and retries.

### 10.3 Field Detection Module
Responsibilities:
- inspect DOM,
- detect input elements,
- extract labels/placeholders/names/ids,
- infer field type.

### 10.4 Rule Inference Module
Responsibilities:
- infer constraints from HTML attributes and field metadata,
- detect maxlength, minlength, type, required, pattern, min, max.

### 10.5 Test Generator Module
Responsibilities:
- create valid and invalid inputs,
- create boundary cases,
- create fuzz inputs,
- generate field-wise test matrix.

### 10.6 Execution Module
Responsibilities:
- open page,
- populate fields,
- submit form,
- capture page state and response.

### 10.7 Result Analyzer Module
Responsibilities:
- compare expected vs observed behavior,
- decide accepted/rejected,
- detect missing validation,
- log errors or odd behavior.

### 10.8 Report Module
Responsibilities:
- build summary tables,
- create pass/fail counts,
- show observed field constraints,
- export report as HTML/JSON/CSV.

---

## 11. Data Model

### 11.1 Field Schema
```json
{
  "fieldId": "phone_1",
  "label": "Phone Number",
  "name": "phone",
  "type": "text",
  "required": true,
  "minLength": 10,
  "maxLength": 10,
  "pattern": "^[0-9]{10}$"
}
```

### 11.2 Test Case Schema
```json
{
  "testCaseId": "tc_001",
  "fieldId": "phone_1",
  "inputValue": "1234567890",
  "category": "valid",
  "expected": "accept",
  "observed": "accept",
  "status": "pass"
}
```

### 11.3 Run Result Schema
```json
{
  "runId": "run_001",
  "url": "https://example.com/form",
  "fieldsDetected": 5,
  "testsExecuted": 42,
  "testsPassed": 38,
  "testsFailed": 4
}
```

---

## 12. Flowchart

```text
Start
  ↓
User enters URL
  ↓
Open page in Playwright
  ↓
Detect form fields
  ↓
Infer field metadata and constraints
  ↓
Generate test cases for each field
  ↓
For each test case:
   - fill field values
   - submit form
   - capture response
   - classify result
  ↓
Store logs/screenshots/results
  ↓
Aggregate field-wise summary
  ↓
Generate final report
  ↓
End
```

---

## 13. Testing Strategy Concepts

### 13.1 Boundary Value Testing
Generate values around limits.
Example:
- if max length is 10, test 9, 10, 11.

### 13.2 Equivalence Partitioning
Split input space into groups.
Example:
- valid digits,
- alphabetic input,
- special characters,
- empty values.

### 13.3 Negative Testing
Try invalid inputs to ensure the system rejects them.

### 13.4 Fuzz Testing
Try unusual, random, oversized, or malformed values.

### 13.5 Pairwise Testing
Later phase optimization for combinations across multiple fields.

---

## 14. Phase Plan

# Phase 1: Core MVP

## Objective
Make the system work for a simple form URL with text fields and generate a basic report.

## Features
- URL input.
- Page loading using Playwright.
- Detect text fields and textarea.
- Extract label, name, placeholder, maxlength, minlength, required, pattern.
- Generate basic test cases:
  - empty value,
  - short value,
  - exact boundary value,
  - long value,
  - alphabetic value,
  - numeric value,
  - special character value.
- Submit the form.
- Detect whether submission was accepted or rejected.
- Capture screenshots on failures.
- Generate a simple HTML/JSON report.

## Why this first
This proves the end-to-end pipeline with the least complexity.

---

# Phase 2: Intelligent Rule Handling

## Objective
Improve test quality and field understanding.

## Features
- Support more input types:
  - email,
  - password,
  - number,
  - date,
  - select dropdown.
- Add better rule inference from HTML attributes.
- Generate richer input categories:
  - boundary,
  - unicode,
  - long strings,
  - script-like input,
  - SQL-like input,
  - whitespace-only input.
- Track test coverage so repeated cases are avoided.
- Add per-field accepted range detection.
- Compare client-side vs server-side validation behavior when possible.

## Why this second
Once the basic engine works, this phase improves correctness and usefulness of the report.

---

# Phase 3: Scalable Reporting and Advanced Automation

## Objective
Make the product useful as a testing tool, not just a demo.

## Features
- Multi-field test combinations.
- Pairwise testing for field combinations.
- A dashboard view for run history.
- Export reports to HTML, JSON, and CSV.
- Aggregated summaries across multiple runs.
- Better failure classification:
  - validation error,
  - silent acceptance,
  - crash,
  - timeout,
  - unexpected redirect.
- Optional self-healing locators for unstable UI selectors.
- Cross-browser runs if needed.

## Why this third
This makes the tool more production-like and usable for repeated testing.

---

## 15. Expected Report Structure

### Summary Section
- URL tested
- date/time
- total fields
- total tests
- pass rate
- fail count

### Field-wise Section
For each field:
- field name
- field type guessed
- constraints observed
- test values tried
- result for each test
- screenshots for failures
- notes on accepted length/format

### Failure Section
- failed test case
- reason
- screenshot path
- error message if available

### Insights Section
- accepted length range
- likely format expectation
- fields with weak or missing validation

---

## 16. Important Design Decisions

### Decision 1: Deterministic First, AI Later
Do not begin with AI inference. Build deterministic rule extraction and test generation first.

### Decision 2: Focus on Text Fields First
Text fields are easiest and most common. Support them before expanding to complex elements.

### Decision 3: Report Observed Behavior, Not Assumed Truth
The system should report what it observed, such as “10 digits accepted,” rather than claiming business rules it cannot verify.

### Decision 4: Keep Phase 1 Small
A working MVP that handles a small set of form fields is better than a large unfinished system.

---

## 17. Risks and Limitations

- CAPTCHA may block automation.
- OTP-based flows will break full automation.
- Dynamic React/SPA forms may require waiting logic.
- Some validations happen only after backend submission.
- Very dynamic selectors may need fallback locator strategies.
- Sites may block repeated automated requests.

---

## 18. Success Criteria

The project is successful if it can:
- take a form URL,
- detect fields reliably,
- generate useful test inputs,
- run tests automatically,
- classify outcomes,
- generate a report that clearly shows accepted and rejected values.

---

## 19. Suggested Development Order

1. Build URL loader and Playwright page opener.
2. Add field detection.
3. Add metadata extraction from HTML.
4. Implement test case generator for text fields.
5. Run a single test case end-to-end.
6. Expand to multiple cases per field.
7. Add result detection and screenshots.
8. Add report generation.
9. Add more field types.
10. Add pairwise testing and coverage tracking.

---

## 20. Final One-Line Description

A browser automation tool that takes a form URL, discovers input fields, generates boundary and invalid test values automatically, runs them through the form, and produces a detailed validation report.
