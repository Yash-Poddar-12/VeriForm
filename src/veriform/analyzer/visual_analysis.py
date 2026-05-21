"""
veriform.analyzer.visual_analysis
=================================
Perceptual screenshot diffing using ImageHash.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from pathlib import Path

try:
    from PIL import Image
    import imagehash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False

from veriform.utils.logging import get_logger

logger = get_logger(__name__)

class VisualAnalysisPipeline:
    def __init__(self):
        # Configurable thresholds
        self.minor_drift_threshold = 5
        self.major_drift_threshold = 12

    def compute_visual_drift(self, img_path_a: Path, img_path_b: Path) -> Dict[str, Any]:
        """Compare two screenshots using perceptual hashing."""
        if not IMAGEHASH_AVAILABLE:
            logger.warning("ImageHash or Pillow not installed. Skipping visual diff.")
            return {"error": "ImageHash not available"}
            
        if not img_path_a.exists() or not img_path_b.exists():
            return {"error": "One or both images missing"}
            
        try:
            hash_a = imagehash.phash(Image.open(img_path_a))
            hash_b = imagehash.phash(Image.open(img_path_b))
            
            distance = hash_a - hash_b
            
            classification = "equivalent"
            if distance > self.major_drift_threshold:
                classification = "major_drift"
            elif distance > self.minor_drift_threshold:
                classification = "minor_drift"
                
            return {
                "distance": distance,
                "classification": classification,
                "hash_a": str(hash_a),
                "hash_b": str(hash_b)
            }
        except Exception as e:
            logger.error(f"Visual analysis failed: {e}")
            return {"error": str(e)}
