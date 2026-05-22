import json
from typing import List
from veriform_core.probe_result import ProbeResult

class JsonReporter:
    @staticmethod
    def export(results: List[ProbeResult], output_path: str):
        data = [r.model_dump() for r in results]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
