"""
tests/test_orchestrator.py
==========================
Smoke + integration tests for orchestrator contracts.
"""

from __future__ import annotations

from veriform.models.schemas import RunSummarySchema
from veriform.orchestrator.orchestrator import run, run_single_page

from fake_playwright import FakePage


class TestOrchestratorFlow:
    async def test_run_returns_run_summary_schema(self):
        summary = await run("https://example.com/form")
        assert isinstance(summary, RunSummarySchema)

    async def test_run_id_is_non_empty(self):
        summary = await run("https://example.com/form")
        assert summary.run_id
        assert len(summary.run_id) > 0

    async def test_target_url_is_preserved(self):
        url = "https://example.com/test-form"
        summary = await run(url)
        assert summary.target_url == url

    async def test_timestamp_is_set(self):
        summary = await run("https://example.com/form")
        assert summary.timestamp is not None


class TestOrchestratorSinglePageFlow:
    async def test_run_single_page_with_injected_page(self, workspace_tmp_path):
        fake_page = FakePage(
            controls=[
                {
                    "name": "mobile_number",
                    "dom_id": "mobile",
                    "type": "text",
                    "label": "Mobile Number",
                    "required": True,
                    "min_length": 10,
                    "max_length": 10,
                    "pattern": "[0-9]{10}",
                    "min_val": None,
                    "max_val": None,
                },
                {
                    "name": "loan_account_number",
                    "dom_id": "loan-account",
                    "type": "text",
                    "label": "Loan Account Number",
                    "required": True,
                    "min_length": 8,
                    "max_length": 16,
                    "pattern": "[0-9]{8,16}",
                    "min_val": None,
                    "max_val": None,
                },
                {
                    "name": "dob",
                    "dom_id": "dob",
                    "type": "date",
                    "label": "Date of Birth",
                    "required": True,
                    "min_length": None,
                    "max_length": None,
                    "pattern": None,
                    "min_val": None,
                    "max_val": None,
                },
                {
                    "name": "application_reference_number",
                    "dom_id": "application-ref",
                    "type": "text",
                    "label": "Application Reference Number",
                    "required": True,
                    "min_length": 6,
                    "max_length": 20,
                    "pattern": "[A-Za-z0-9]{6,20}",
                    "min_val": None,
                    "max_val": None,
                },
            ]
        )

        summary = await run_single_page(
            target_url="https://example.com/form",
            page=fake_page,
            reports_root=workspace_tmp_path,
        )

        assert summary.metrics.total_fields_detected == 4
        assert summary.metrics.total_tests_executed > 0
        assert (workspace_tmp_path / summary.run_id / "report.json").exists()
        assert (workspace_tmp_path / summary.run_id / "report.html").exists()


class TestOrchestratorAPI:
    async def test_health_endpoint(self, api_client):
        response = await api_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_post_run_returns_202(self, api_client):
        response = await api_client.post(
            "/runs/", json={"target_url": "https://example.com/form"}
        )
        assert response.status_code == 202
        body = response.json()
        assert "run_id" in body
        assert "metrics" in body

    async def test_post_run_invalid_url_returns_422(self, api_client):
        response = await api_client.post("/runs/", json={"target_url": "not-a-url"})
        assert response.status_code == 422
