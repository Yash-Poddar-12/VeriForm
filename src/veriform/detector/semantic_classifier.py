import re
from typing import Dict, List, Optional, Tuple

class SemanticClassifier:
    """
    Deterministically classifies form fields into semantic types using a priority scoring system.
    
    Priority Score Weighting:
    - exact attribute match (inputmode, autocomplete): 0.5
    - exact name/id match: 0.4
    - regex name/id match: 0.3
    - placeholder match: 0.2
    - label match: 0.1
    """
    
    SEMANTIC_TYPES = {
        "phone": {
            "attributes": {"inputmode": ["tel"], "autocomplete": ["tel"]},
            "name_exact": ["phone", "mobile", "contact", "cell"],
            "name_regex": r"(phone|mobile|tel|contact|cell|number)",
            "keywords": ["phone", "mobile number", "contact number"]
        },
        "email": {
            "attributes": {"type": ["email"], "autocomplete": ["email"]},
            "name_exact": ["email", "email_address", "mail"],
            "name_regex": r"email",
            "keywords": ["email", "e-mail"]
        },
        "aadhaar": {
            "attributes": {},
            "name_exact": ["aadhaar", "aadhar", "uid"],
            "name_regex": r"(aadhaar|aadhar|uid)",
            "keywords": ["aadhaar", "aadhar", "unique id"]
        },
        "pan": {
            "attributes": {},
            "name_exact": ["pan", "pancard"],
            "name_regex": r"(pan_?card|pan\b)",
            "keywords": ["pan", "pan card"]
        },
        "otp": {
            "attributes": {"autocomplete": ["one-time-code"]},
            "name_exact": ["otp", "code", "verification"],
            "name_regex": r"(otp|code|verification|token)",
            "keywords": ["otp", "verification code", "one time password"]
        },
        "dob": {
            "attributes": {"type": ["date"], "autocomplete": ["bday"]},
            "name_exact": ["dob", "date_of_birth", "birthdate"],
            "name_regex": r"(dob|birth|dateofbirth)",
            "keywords": ["dob", "date of birth", "birth date"]
        },
        "pincode": {
            "attributes": {"autocomplete": ["postal-code"]},
            "name_exact": ["pincode", "zip", "zipcode", "postal"],
            "name_regex": r"(pin|zip|postal|postcode)",
            "keywords": ["pincode", "zip code", "postal code"]
        },
        "name": {
            "attributes": {"autocomplete": ["name", "given-name", "family-name"]},
            "name_exact": ["name", "firstname", "lastname", "fullname"],
            "name_regex": r"name",
            "keywords": ["name", "first name", "last name", "full name"]
        },
        "password": {
            "attributes": {"type": ["password"], "autocomplete": ["current-password", "new-password"]},
            "name_exact": ["password", "pwd", "pass"],
            "name_regex": r"(password|pwd|pass)",
            "keywords": ["password"]
        },
        "numeric_amount": {
            "attributes": {"inputmode": ["numeric", "decimal"]},
            "name_exact": ["amount", "price", "cost", "salary", "income"],
            "name_regex": r"(amount|price|cost|salary|income)",
            "keywords": ["amount", "salary", "price"]
        }
    }

    @classmethod
    def classify(cls, metadata: Dict[str, Optional[str]]) -> Tuple[Optional[str], float, List[str]]:
        """
        Classify a field based on extracted metadata.
        Returns: (semantic_type, confidence, matched_signals)
        """
        best_type = None
        best_score = 0.0
        best_signals = []
        
        # Normalize inputs for matching
        name = (metadata.get("name") or "").lower()
        dom_id = (metadata.get("dom_id") or "").lower()
        placeholder = (metadata.get("placeholder") or "").lower()
        label = (metadata.get("label") or "").lower()
        
        name_id = f"{name} {dom_id}".strip()
        
        for sem_type, rules in cls.SEMANTIC_TYPES.items():
            score = 0.0
            signals = []
            
            # 1. Attribute matching (0.5)
            for attr_name, expected_vals in rules.get("attributes", {}).items():
                actual_val = (metadata.get(attr_name) or "").lower()
                if actual_val in expected_vals:
                    score += 0.5
                    signals.append(f"{attr_name}={actual_val}")
            
            # 2. Exact Name/ID matching (0.4)
            if name in rules.get("name_exact", []) or dom_id in rules.get("name_exact", []):
                score += 0.4
                signals.append(f"name/id exactly matches {sem_type}")
                
            # 3. Regex Name/ID matching (0.3)
            elif re.search(rules.get("name_regex", ""), name_id):
                score += 0.3
                signals.append(f"name/id regex matches {sem_type}")
                
            # 4. Placeholder keyword match (0.2)
            for kw in rules.get("keywords", []):
                if kw in placeholder:
                    score += 0.2
                    signals.append(f"placeholder contains '{kw}'")
                    break # only count once for placeholder
                    
            # 5. Label keyword match (0.1)
            for kw in rules.get("keywords", []):
                if kw in label:
                    score += 0.1
                    signals.append(f"label contains '{kw}'")
                    break # only count once for label
                    
            if score > best_score:
                best_score = score
                best_type = sem_type
                best_signals = signals
        
        # Cap confidence at 0.99
        best_score = min(best_score, 0.99)
        
        if best_score > 0.0:
            return best_type, best_score, best_signals
        
        return None, 0.0, []
