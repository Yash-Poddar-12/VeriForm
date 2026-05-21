from __future__ import annotations

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

class HtmlExporter:
    """Exports RunArtifact to a highly polished HTML discovery report."""
    
    def __init__(self, template_dir: str = "templates"):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        
    def export(self, artifact, output_path: Path):
        template = self.env.get_template("discovery_report.html.j2")
        
        html_content = template.render(
            run_id=artifact.run_id,
            target_url=artifact.target_url,
            metrics=artifact.metrics,
            fields=artifact.validation_contract.fields
        )
        
        output_path.write_text(html_content, encoding="utf-8")
