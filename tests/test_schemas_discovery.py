import pytest
from datetime import datetime
from veriform.schemas.discovery import ValidationContract, FieldSpecification, RegexInference
from veriform.schemas.reports import FinalDiscoveryReport, ExecutiveSummary, ExecutiveSummaryMetrics

def test_validation_contract_serialization():
    field = FieldSpecification(
        field_id="field_01",
        name="mobile_number",
        semantic_type="phone",
        required=True,
        min_length=10,
        max_length=10,
        allowed_charsets=["digits"],
        inferred_regex=RegexInference(
            pattern="^[6-9][0-9]{9}$",
            confidence=0.95,
            examples_accepted=["9876543210"],
            examples_rejected=["12345", "abcdefghij"],
            description="10 digit Indian mobile number starting with 6-9"
        ),
        html_attributes={"placeholder": "Enter mobile"},
        validation_messages=["Invalid mobile number"]
    )
    
    contract = ValidationContract(
        run_id="run_123",
        target_url="https://example.com",
        fields=[field]
    )
    
    # Dump to JSON
    json_data = contract.model_dump_json()
    assert "mobile_number" in json_data
    assert "^[6-9][0-9]{9}$" in json_data
    
    # Reload from JSON
    reloaded = ValidationContract.model_validate_json(json_data)
    assert len(reloaded.fields) == 1
    assert reloaded.fields[0].inferred_regex.confidence == 0.95

def test_reports_serialization():
    metrics = ExecutiveSummaryMetrics(
        total_fields=1,
        fully_specified_fields=1,
        total_mutations_tested=10,
        run_duration_ms=4500
    )
    summary = ExecutiveSummary(
        run_id="run_123",
        target_url="https://example.com",
        timestamp=datetime.now(),
        mode="discovery_mode",
        metrics=metrics
    )
    
    json_data = summary.model_dump_json()
    reloaded = ExecutiveSummary.model_validate_json(json_data)
    assert reloaded.mode == "discovery_mode"
    assert reloaded.metrics.total_fields == 1
