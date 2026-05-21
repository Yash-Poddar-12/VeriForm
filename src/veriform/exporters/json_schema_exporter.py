from __future__ import annotations
from typing import Dict, Any
from pydantic import BaseModel

class JsonSchemaExporter:
    """Exports validation contracts to JSON Schema Draft 2020-12."""
    
    def export(self, contract: BaseModel) -> Dict[str, Any]:
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for field in contract.fields:
            if not field.synthesized_regex:
                continue
                
            field_schema = {"type": "string"}
            syn = field.synthesized_regex
            
            if syn.regex:
                field_schema["pattern"] = syn.regex
                
            if field.min_length is not None:
                field_schema["minLength"] = field.min_length
                
            if field.max_length is not None:
                field_schema["maxLength"] = field.max_length
                
            if field.semantic_type == "email":
                field_schema["format"] = "email"
            elif field.semantic_type == "date":
                field_schema["format"] = "date"
                
            schema["properties"][field.name] = field_schema
            
            if syn.required:
                schema["required"].append(field.name)
                
        if not schema["required"]:
            del schema["required"]
            
        return schema
