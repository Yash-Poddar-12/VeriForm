from __future__ import annotations
from typing import Dict, Any
from pydantic import BaseModel

class OpenApiExporter:
    """Exports validation contracts to OpenAPI 3.1 schema definitions."""
    
    def export(self, contract: BaseModel, title: str = "VeriForm Extracted Schema") -> Dict[str, Any]:
        properties = {}
        required = []
        
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
                
            if syn.description:
                field_schema["description"] = syn.description
                
            if syn.accepted_examples:
                field_schema["examples"] = syn.accepted_examples
                
            properties[field.name] = field_schema
            
            if syn.required:
                required.append(field.name)
                
        schema_obj = {
            "type": "object",
            "title": title,
            "properties": properties
        }
        
        if required:
            schema_obj["required"] = required
            
        return schema_obj
