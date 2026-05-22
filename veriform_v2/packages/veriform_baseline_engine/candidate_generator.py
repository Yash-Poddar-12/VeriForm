from veriform_core.classifications import FieldType

class CandidateGenerator:
    """Generates naive inputs without AI for strict deterministic evaluation."""
    def __init__(self):
        self.heuristics = {
            "email": ["test@example.com", "admin@domain.co", "invalid-email"],
            "phone": ["9876543210", "123", "0000000000"],
            "pan": ["ABCDE1234F", "12345", "ZZZZZ9999Z"],
            "numeric": ["12345", "00000", "abc"],
            "text": ["John Doe", "A", ""]
        }
        
    def guess_type(self, field_metadata: dict) -> FieldType:
        label = field_metadata.get('label', '').lower()
        id_str = field_metadata.get('id', '').lower()
        type_str = field_metadata.get('type', '').lower()
        
        if 'email' in label or 'email' in id_str or type_str == 'email':
            return FieldType.EMAIL
        if 'phone' in label or 'mobile' in label:
            return FieldType.PHONE
        if 'pan' in label or 'pan' in id_str:
            return FieldType.PAN
        return FieldType.GENERIC_TEXT
        
    def generate_candidate(self, field_type: FieldType, attempt: int = 0) -> str:
        options = self.heuristics.get(field_type.value, ["Generic Input"])
        return options[attempt % len(options)]
