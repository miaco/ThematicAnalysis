"""
Skill: Grounding / traceability check for themes.
"""

from models.schemas import Theme, Code, Quote


def check_grounding(themes: list[Theme], codes: list[Code], quotes: list[Quote]) -> list[str]:
    """
    Verify traceability: each theme should trace back to codes,
    which trace to quotes. Returns a list of issue descriptions.
    """
    issues = []
    code_map = {c.id: c for c in codes}
    quote_ids = {q.id for q in quotes}

    for theme in themes:
        if not theme.code_ids:
            issues.append(f"Theme '{theme.name}': No codes linked")
            continue

        missing_codes = [cid for cid in theme.code_ids if cid not in code_map]
        if missing_codes:
            issues.append(
                f"Theme '{theme.name}': {len(missing_codes)} referenced codes not found in session codes"
            )

        total_quote_refs = 0
        for cid in theme.code_ids:
            code = code_map.get(cid)
            if code:
                valid_quote_refs = [qid for qid in code.quote_ids if qid in quote_ids]
                total_quote_refs += len(valid_quote_refs)

        if total_quote_refs < 3:
            issues.append(
                f"Theme '{theme.name}': Only {total_quote_refs} verifiable quote reference(s). "
                "Recommend at least 3 for robust grounding."
            )

    return issues
