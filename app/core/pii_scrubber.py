import re

class PIIScrubber:
    """
    Ensures data privacy by removing or masking sensitive information 
    BEFORE it is stored or processed by external logging systems.
    """
    
    PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "api_key": r"sk-[a-zA-Z0-9]{32,}"
    }

    @staticmethod
    def scrub(text: str) -> str:
        """
        Replaces found PII patterns with [REDACTED_TYPE].
        """
        if not text:
            return ""
            
        anonymized_text = text
        for label, pattern in PIIScrubber.PATTERNS.items():
            anonymized_text = re.sub(pattern, f"[{label.upper()}_REDACTED]", anonymized_text)
            
        return anonymized_text
