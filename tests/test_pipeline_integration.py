import pytest
import json
from pathlib import Path
from veriform.orchestrator.pipeline import PipelineOrchestrator
from veriform.schemas.mutations import MutationProfile
from fake_playwright import FakePage

@pytest.fixture
def fake_page():
    return FakePage(
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
            }
        ]
    )

@pytest.mark.asyncio
async def test_pipeline_end_to_end(fake_page, workspace_tmp_path):
    orchestrator = PipelineOrchestrator(
        page=fake_page,
        run_id="run-test-e2e",
        profile=MutationProfile.LIGHTWEIGHT
    )
    
    artifact = await orchestrator.run("https://example.com", workspace_tmp_path)
    
    assert artifact.run_id == "run-test-e2e"
    assert artifact.metrics.total_fields == 1
    assert artifact.metrics.processed_fields == 1
    assert artifact.metrics.total_probes_executed > 0
    assert len(artifact.validation_contract.fields) == 1
    
    # Check exported files
    run_dir = workspace_tmp_path / "run-test-e2e"
    
    assert (run_dir / "validation_contract.json").exists()
    assert (run_dir / "raw_probe_results.json").exists()
    assert (run_dir / "execution_metrics.json").exists()
    assert (run_dir / "inferred_schema.json").exists()
    assert (run_dir / "openapi.json").exists()
    
    # Validate OpenAPI Output
    openapi_txt = (run_dir / "openapi.json").read_text()
    openapi_dict = json.loads(openapi_txt)
    
    assert "mobile_number" in openapi_dict["properties"]
    assert openapi_dict["properties"]["mobile_number"]["type"] == "string"
    assert "required" in openapi_dict
    assert "mobile_number" in openapi_dict["required"]

def test_json_schema_exporter():
    from veriform.exporters.json_schema_exporter import JsonSchemaExporter
    from veriform.schemas.discovery import ValidationContract, FieldSpecification, RegexSynthesisResult
    
    contract = ValidationContract(
        run_id="test",
        target_url="http",
        fields=[
            FieldSpecification(
                field_id="1",
                name="email_addr",
                semantic_type="email",
                synthesized_regex=RegexSynthesisResult(
                    field_id="1",
                    regex=".*@.*",
                    confidence=0.9,
                    description="email",
                    required=True
                )
            )
        ]
    )
    
    exporter = JsonSchemaExporter()
    schema = exporter.export(contract)
    
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["email_addr"]["format"] == "email"
    assert schema["properties"]["email_addr"]["pattern"] == ".*@.*"
    assert "email_addr" in schema["required"]
