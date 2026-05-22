# VeriForm 2.0

> [!NOTE]  
> **This is the active development branch.** VeriForm 2.0 is the successor to the original VeriForm (V1) located in the root repository. V1 relied on static parsing and heuristics, whereas V2 has been completely re-architected to use dynamic browser-based differential fuzzing as the sole source of truth.

VeriForm 2.0 is a next-generation autonomous behavioral form fuzzer and validation inference platform. It actively interacts with web forms using a real browser to discover form logic, generate inputs, execute differential mutation tests, and deterministically attribute validation failures.

## Philosophy
* **The Browser is the Absolute Source of Truth:** No validation rule is assumed true unless proven by an actual browser submission and observed response.
* **Deterministic Execution:** No arbitrary `sleep()` calls. Synchronization relies strictly on deterministic browser events (e.g., `networkidle`, DOM mutation timestamps).
* **Valid Baseline First:** Aggressive mutation testing only occurs *after* discovering a known-valid submission state.
* **Differential Isolation:** Only one field is mutated at a time relative to a valid baseline to perfectly isolate causality.
* **Replayability & Hashability:** Every test and state is perfectly reproducible, allowing for cryptographic-grade evidence generation.

## Architecture

The system operates as an event-driven state machine managing isolated Playwright browser contexts:
1. **SyncManager & DOMStabilityDetector:** Provides synchronous hooks into browser lifecycle events, bypassing native async flakiness and ensuring precise network payload monitoring and DOM stability checks.
2. **RollbackEngine:** Reverts the browser state perfectly between mutation probes to ensure zero pollution between tests.
3. **ProbeExecutor:** Deterministically fast-forwards to the baseline state and injects mutations while strictly bounding the execution and observation windows.
4. **ValidationObserver & AttributionEngine:** Scrapes DOM and Network layer validation failures following a probe and attributes them dynamically to the mutated field.
5. **Hostile Benchmark Suite:** A local web server featuring maliciously complex and flaky form implementations (e.g., optimistic UI patterns, shadow DOMs, deferred timeouts) to guarantee VeriForm 2.0 remains deterministic under extreme conditions.

## Current Status
**Milestone 5:** The core fuzzing engine, network attribution logic, and benchmark suite are fully operational and integrated. The system is capable of accurately running parallel mutation candidates, recording evidence hashes, intercepting delayed/optimistic network requests reliably, and deduplicating events without listener leakages.

## Requirements
* Python 3.12+
* [Playwright](https://playwright.dev/python/) (`pip install playwright` then `playwright install chromium`)
* [FastAPI](https://fastapi.tiangolo.com/) & Uvicorn (For the hostile benchmark suite)

## Getting Started

### 1. Start the Hostile Benchmark Server
The benchmark server hosts the trap implementations that VeriForm validates itself against.
```bash
uvicorn packages.benchmark_server.server:app --host 127.0.0.1 --port 8000
```

### 2. Run the Differential Fuzzing Harness
The harness runs against the local benchmark traps to prove the orchestration logic.
```bash
python packages/benchmark_runner/mutation_harness.py
```

### Example Diagnostic Output
When the mutation harness is run, it will produce deterministic validation evidence and attribution scores:
```
INFO:root:Starting Differential Mutation for field: pan
INFO:root:Testing Candidate: 12345ABCDE
INFO:root:[ProbeExecutor] Filled 'pan' = '12345ABCDE'
INFO:root:[ProbeExecutor] Clicked. Waiting 2000ms for JS timers + network...
INFO:root:[Delta Capture] Extracted 0 network failures from SyncManager.
INFO:root:Result Hash: dcd40207177bbf57aa2f8075bfcb9ec712477e0f58b5a9372d55d7ca44716b38 | Confidence: 0.0

INFO:root:Testing Candidate: ABCDE1234
INFO:root:[ProbeExecutor] Filled 'pan' = 'ABCDE1234'
INFO:root:[ProbeExecutor] Clicked. Waiting 2000ms for JS timers + network...
INFO:root:[Delta Capture] Extracted 1 network failures from SyncManager.
INFO:root:[Attribution] Solitary Match (Network): http://127.0.0.1:8000/trigger_400
INFO:root:Result Hash: 4c20441f30b8b87703dcb0e6e2fa967d7a1ba7d090e57132037847bad545829e | Confidence: 0.7

=== FINAL MUTATION ATTRIBUTIONS ===
Candidate: '12345ABCDE' -> UNKNOWN | Score: 0.0 | Errors: []
Candidate: 'ABCDE1234' -> CONFIRMED_REJECTED | Score: 0.7 | Errors: ['Network Rejection: http://127.0.0.1:8000/trigger_400']
Candidate: 'ABCDE1234F' -> UNKNOWN | Score: 0.0 | Errors: []
Candidate: 'ABCDE1234FG' -> CONFIRMED_REJECTED | Score: 0.7 | Errors: ['Network Rejection: http://127.0.0.1:8000/trigger_400']
```
