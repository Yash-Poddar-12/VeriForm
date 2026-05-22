import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../packages')))

from veriform_attribution.confidence_scoring import ConfidenceScorer

def test_confidence_scorer():
    scorer = ConfidenceScorer()
    assert scorer.score({"exact_match": True}) == 1.0
    assert scorer.score({"solitary_mutation": True}) == 0.7
    assert scorer.score({}) == 0.0
