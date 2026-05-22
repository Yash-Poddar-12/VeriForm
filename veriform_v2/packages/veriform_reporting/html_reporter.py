from typing import List
from veriform_core.probe_result import ProbeResult

class HtmlReporter:
    @staticmethod
    def generate(results: List[ProbeResult], output_path: str):
        html = ["<html><head><title>VeriForm Report</title></head><body style='font-family: sans-serif'><h1>Validation Attributions</h1>"]
        for r in results:
            html.append(f"<div style='border: 1px solid #ccc; padding: 10px; margin: 10px 0;'>")
            html.append(f"<h3>Field: {r.mutated_field}</h3>")
            html.append(f"<p><strong>Candidate:</strong> {r.candidate_value}</p>")
            html.append(f"<p><strong>Confidence:</strong> {r.confidence_score}</p>")
            html.append(f"<p><strong>Errors Inferred:</strong> {r.attribution.get('inferred_errors', [])}</p>")
            html.append(f"<p><small>Evidence Hash: {r.evidence_hash}</small></p>")
            html.append("</div>")
        html.append("</body></html>")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\\n".join(html))
