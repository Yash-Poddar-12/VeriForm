# Project Vision

## Overview
The URL-Based Form Test Automation Platform is a browser-based testing tool that automates the discovery, testing, and validation of web form input constraints. Given a URL, the system automatically detects fields, generates extensive test values, submits the form, and observes the results to produce a comprehensive validation report.

## Value Proposition
To drastically reduce manual form-testing effort and human error by automatically discovering input constraints (valid/invalid value ranges, boundary lengths, format restrictions, and field-specific acceptance rules).

## Primary Use Case
**Input:** A target web page URL containing one or more standard forms.
**Action:** The system inspects the DOM, detects inputs, classifies them, generates valid/invalid/boundary test data, and runs browser automation to submit these combinations.
**Output:** A structured report detailing the detected fields, test case combinations executed, and outcomes (pass/fail/error), along with visual evidence (screenshots) for failures.

## Project Goals
- Build an end-to-end automated pipeline from URL input to final validation report.
- Deliver a reliable, deterministic core engine before introducing any AI heuristics.
- Ensure the system is extensible to support complex inputs, multi-field workflows, and varying validation behaviors across web applications.

## Scope
### In Scope
- Testing public or internal web pages containing standard HTML forms.
- Support for common inputs: text, email, number, textarea, password, select.
- Automated generation of boundary, invalid, and fuzz-style test data.
- Execution via headless/headed browser automation (Playwright).
- Comprehensive result collection, screenshot capture, and reporting.

### Out of Scope (MVP & Near-term)
- CAPTCHA solving and OTP handling.
- Deep session automation or complex login states.
- Highly dynamic, multi-step React/SPA wizard flows (for initial phases).
- Testing native mobile applications or PDF forms.
- File upload testing (deferred to later phases).

## Risks and Assumptions
### Risks
- **Anti-bot Mechanisms:** CAPTCHAs or Web Application Firewalls (WAFs) may block automated browser sessions.
- **Dynamic Selectors:** Frameworks generating dynamic element IDs/classes may cause flaky field detection.
- **Asynchronous Validation:** Client-side SPA validations and delayed server responses might require complex wait strategies.
### Assumptions
- Target forms utilize standard or recognizable HTML5 input elements and attributes.
- The environment has network access to the target URLs.
- The MVP can focus on deterministic rule extraction without relying on non-deterministic AI models.
