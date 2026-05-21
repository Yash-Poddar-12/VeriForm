"""
veriform.services.artifact_service
==================================
File-backed artifact storage abstractions.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import List

from veriform.config import settings
from veriform.persistence.database import get_session
from veriform.persistence.models import WorkflowArtifact
from veriform.persistence.repositories import ArtifactRepository
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


class ArtifactService:
    def __init__(self):
        self.base_dir = settings.artifact_storage_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_run_dir(self, run_id: str) -> Path:
        run_dir = self.base_dir / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    async def store_screenshot(self, run_id: str, state_hash: str, image_bytes: bytes) -> WorkflowArtifact:
        """Store screenshot and register in database."""
        run_dir = self._get_run_dir(run_id)
        ss_dir = run_dir / "screenshots"
        ss_dir.mkdir(exist_ok=True)
        
        file_path = ss_dir / f"{state_hash}.png"
        file_path.write_bytes(image_bytes)
        
        async with get_session() as db:
            repo = ArtifactRepository(db)
            return await repo.register_artifact(run_id, "screenshot", str(file_path))

    async def store_trace_log(self, run_id: str, trace_lines: List[str]) -> WorkflowArtifact:
        """Store deterministic JSONL trace log."""
        run_dir = self._get_run_dir(run_id)
        traces_dir = run_dir / "traces"
        traces_dir.mkdir(exist_ok=True)
        
        file_path = traces_dir / "trace.jsonl"
        with file_path.open("w", encoding="utf-8") as f:
            for line in trace_lines:
                f.write(line + "\n")
                
        async with get_session() as db:
            repo = ArtifactRepository(db)
            return await repo.register_artifact(run_id, "trace", str(file_path))

    async def export_run_bundle(self, run_id: str) -> str:
        """Export all run artifacts to a ZIP file."""
        run_dir = self._get_run_dir(run_id)
        export_dir = self.base_dir / "exports"
        export_dir.mkdir(exist_ok=True)
        
        zip_path = export_dir / f"run_{run_id}.zip"
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in run_dir.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(run_dir))
                    
        return str(zip_path)
