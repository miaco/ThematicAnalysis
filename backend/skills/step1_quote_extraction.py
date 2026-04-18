"""
Skill: Transcript preprocessing and quote accuracy verification.
"""


def detect_language_and_word_count(text: str) -> dict:
    """Basic preprocessing checks for a transcript."""
    words = text.split()
    word_count = len(words)
    # Simple heuristic: check for non-ASCII chars as a proxy for non-English
    ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(len(text), 1)
    language_warning = None
    if ascii_ratio < 0.7:
        language_warning = "Text may contain non-English content (high non-ASCII ratio). Please verify language."
    return {"word_count": word_count, "language_warning": language_warning}


def verify_quote_accuracy(quote_text: str, source_content: str) -> bool:
    """
    Check that a quote exists in the source transcript via normalized
    substring matching on the first 50 characters.
    """
    if len(quote_text.strip()) < 10:
        return True
    normalized_quote = " ".join(quote_text.lower().split())
    normalized_source = " ".join(source_content.lower().split())
    return normalized_quote[:50] in normalized_source
