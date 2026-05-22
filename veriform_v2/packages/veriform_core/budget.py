from dataclasses import dataclass

@dataclass
class ProbeBudget:
    max_form_attempts: int = 50
    max_retries_per_field: int = 10
    max_identical_failures: int = 3
    timeout_ms: int = 300000 # 5 mins
