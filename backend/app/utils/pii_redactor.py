import re


def redact_pii(text: str) -> str:
    """Redact emails, phone numbers, and SSNs from log text."""
    text = re.sub(r'[\w.+]+@[\w.]+\.\w+', '[EMAIL]', text)
    text = re.sub(r'\+?[\d\s\-()]{10,15}', '[PHONE]', text)
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    return text
