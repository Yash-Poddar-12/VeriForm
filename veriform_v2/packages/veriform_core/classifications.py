from enum import Enum

class FieldType(Enum):
    EMAIL = "email"
    PHONE = "phone"
    PAN = "pan"
    LOAN_ID = "loan_id"
    PASSWORD = "password"
    DATE = "date"
    OTP = "otp"
    NUMERIC = "numeric"
    GENERIC_TEXT = "text"
