import re
from typing import Literal

# Character range patterns for Indian languages
LANGUAGE_PATTERNS = {
    "hindi":     re.compile(r'[ऀ-ॿ]'),   # Devanagari
    "tamil":     re.compile(r'[஀-௿]'),   # Tamil
    "telugu":    re.compile(r'[ఀ-౿]'),   # Telugu
    "kannada":   re.compile(r'[ಀ-೿]'),   # Kannada
    "malayalam": re.compile(r'[ഀ-ൿ]'),   # Malayalam
    "gujarati":  re.compile(r'[઀-૿]'),   # Gujarati
    "marathi":   re.compile(r'[ऀ-ॿ]'),   # Same as Hindi (Devanagari)
    "bengali":   re.compile(r'[ঀ-৿]'),   # Bengali
    "english":   re.compile(r'[a-zA-Z]'),
}


def detect_query_language(query: str) -> str:
    """
    Detects the primary language of the query.
    Returns ISO language name for injection into LLM prompt.
    """
    char_counts = {lang: len(pattern.findall(query))
                   for lang, pattern in LANGUAGE_PATTERNS.items()}
    dominant = max(char_counts, key=char_counts.get)
    if char_counts[dominant] == 0:
        return "english"
    return dominant


def get_language_instruction(language: str) -> str:
    """Returns the instruction to add to system prompt for language."""
    if language == "english":
        return ""
    return (
        f"\n\nIMPORTANT: The user's question is in {language.capitalize()}. "
        f"Respond in {language.capitalize()} language throughout your entire response. "
        f"Technical terms and document citations can remain in English."
    )
