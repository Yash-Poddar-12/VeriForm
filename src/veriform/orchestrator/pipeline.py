"""
veriform.orchestrator.pipeline
==============================
Canonical pipeline for deterministic validation discovery.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from veriform.detector.detector import detect_fields
from veriform.mutator.mutation_engine import MutationEngine
from veriform.schemas.mutations import MutationProfile
from veriform.executor.probe_executor import ProbeExecutor
from veriform.inference.dynamic_infer import BehavioralInferencer
from veriform.synthesizer.regex_engine import RegexEngine
from veriform.schemas.discovery import ValidationContract, FieldSpecification
from veriform.exporters.json_schema_exporter import JsonSchemaExporter
from veriform.exporters.openapi_exporter import OpenApiExporter
from veriform.utils.logging import get_logger

logger = get_logger(__name__)
from pydantic import BaseModel

class ExecutionMetrics(BaseModel):
    total_fields: int = 0
    processed_fields: int = 0
    total_probes_executed: int = 0
    avg_confidence: float = 0.0
    duration_ms: int = 0

class RunArtifact(BaseModel):
    run_id: str
    timestamp: datetime
    target_url: str
    execution_profile: MutationProfile
    validation_contract: ValidationContract
    metrics: ExecutionMetrics
    warnings: List[str] = []

class PipelineOrchestrator:
    """End-to-end execution pipeline."""
    
    def __init__(self, page, run_id: str, profile: MutationProfile = MutationProfile.BALANCED):
        self.page = page
        self.run_id = run_id
        self.profile = profile
        self.mutator = MutationEngine(profile=profile)
        self.executor = ProbeExecutor(page)
        self.inferencer = BehavioralInferencer()
        self.synthesizer = RegexEngine()
        
    async def run(self, target_url: str, output_dir: Path) -> RunArtifact:
        start_time = datetime.now()
        warnings = []
        metrics = ExecutionMetrics()
        
        # 1. Setup outputs
        run_dir = output_dir / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Navigation
        try:
            await self.page.goto(target_url, timeout=30000)
            await self.page.wait_for_timeout(2000) # Give forms time to render
        except Exception as e:
            warnings.append(f"Navigation error: {e}")
            
        # 3. Detection
        raw_fields = await detect_fields(self.page, self.run_id)
        metrics.total_fields = len(raw_fields)
        
        field_specs = []
        confidences = []
        raw_probe_history = {}
        
        for field in raw_fields:
            try:
                # 4. Generate Probes
                probes = self.mutator.generate_for_field(field)
                
                # 5. Execute Probes
                results = await self.executor.execute_probes(field, probes)
                metrics.total_probes_executed += len(results)
                raw_probe_history[field.field_id] = [r.model_dump() for r in results]
                
                # 6. Infer Constraints
                constraints = self.inferencer.infer(field, results)
                
                # 7. Synthesize Regex
                syn_result = self.synthesizer.synthesize(field, constraints, results)
                
                confidences.append(syn_result.confidence)
                
                # Aggregate to Spec
                spec = FieldSpecification(
                    field_id=field.field_id,
                    name=field.name or field.field_id,
                    semantic_type=field.semantic_type,
                    required=syn_result.required,
                    min_length=constraints.min_length,
                    max_length=constraints.max_length,
                    synthesized_regex=syn_result,
                    html_attributes={"placeholder": field.placeholder} if field.placeholder else {}
                )
                field_specs.append(spec)
                metrics.processed_fields += 1
                
            except Exception as e:
                logger.error(f"Failed to process field {field.field_id}: {e}")
                warnings.append(f"Failed field {field.field_id}: {str(e)}")
                
        metrics.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        if confidences:
            metrics.avg_confidence = sum(confidences) / len(confidences)
            
        contract = ValidationContract(
            run_id=self.run_id,
            target_url=target_url,
            fields=field_specs
        )
        
        artifact = RunArtifact(
            run_id=self.run_id,
            timestamp=start_time,
            target_url=target_url,
            execution_profile=self.profile,
            validation_contract=contract,
            metrics=metrics,
            warnings=warnings
        )
        
        # 8. Export Artifacts
        self._export_artifacts(run_dir, artifact, raw_probe_history)
        
        return artifact

    def _export_artifacts(self, run_dir: Path, artifact: RunArtifact, probe_history: dict):
        contract_path = run_dir / "validation_contract.json"
        contract_path.write_text(artifact.validation_contract.model_dump_json(indent=2))
        
        probe_path = run_dir / "raw_probe_results.json"
        probe_path.write_text(json.dumps(probe_history, indent=2))
        
        metrics_path = run_dir / "execution_metrics.json"
        metrics_path.write_text(artifact.metrics.model_dump_json(indent=2))
        
        # JSON Schema Export
        js_exporter = JsonSchemaExporter()
        js_schema = js_exporter.export(artifact.validation_contract)
        (run_dir / "inferred_schema.json").write_text(json.dumps(js_schema, indent=2))
        
        # OpenAPI Export
        oa_exporter = OpenApiExporter()
        oa_schema = oa_exporter.export(artifact.validation_contract)
        (run_dir / "openapi.json").write_text(json.dumps(oa_schema, indent=2))
        
        # HTML Report Export
        try:
            from veriform.exporters.html_exporter import HtmlExporter
            html_exporter = HtmlExporter()
            html_exporter.export(artifact, run_dir / "report.html")
        except Exception as e:
            logger.error(f"Failed to export HTML report: {e}")
