"""Tests for DOM state differencing and hashing."""

import pytest
from veriform.detector.state_tracker import _compute_semantic_hash
from veriform.models.schemas import FieldSchema

def test_compute_semantic_hash_ignores_dom_id() -> None:
    fields1 = [
        FieldSchema(
            field_id="f1", run_id="r1", name="email", type="email", required=True, dom_id="react-123"
        )
    ]
    fields2 = [
        FieldSchema(
            field_id="f1", run_id="r1", name="email", type="email", required=True, dom_id="react-456"
        )
    ]
    
    hash1 = _compute_semantic_hash("http://example.com/form", fields1, [])
    hash2 = _compute_semantic_hash("http://example.com/form", fields2, [])
    
    assert hash1 == hash2

def test_compute_semantic_hash_detects_field_changes() -> None:
    fields1 = [
        FieldSchema(
            field_id="f1", run_id="r1", name="email", type="email", required=True
        )
    ]
    fields2 = [
        FieldSchema(
            field_id="f1", run_id="r1", name="email", type="email", required=True
        ),
        FieldSchema(
            field_id="f2", run_id="r1", name="password", type="password", required=True
        )
    ]
    
    hash1 = _compute_semantic_hash("http://example.com/form", fields1, [])
    hash2 = _compute_semantic_hash("http://example.com/form", fields2, [])
    
    assert hash1 != hash2

def test_compute_semantic_hash_detects_validation_changes() -> None:
    fields = [
        FieldSchema(
            field_id="f1", run_id="r1", name="email", type="email", required=True
        )
    ]
    
    hash1 = _compute_semantic_hash("http://example.com/form", fields, [])
    hash2 = _compute_semantic_hash("http://example.com/form", fields, ["Invalid email address"])
    
    assert hash1 != hash2
