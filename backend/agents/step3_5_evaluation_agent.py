"""
Evaluation Agent: Scores codes and themes on four quality criteria
inspired by the TAMA framework (coverage, actionability, distinctiveness, relevance).
Each item receives a score from 1.0 to 5.0 on each criterion.
"""

import json
import os
import re
from datetime import datetime

import anthropic

from models.schemas import Session, EvaluationScores, EvaluationSummary
from orchestration.pipeline_config import MODELS
from skills.step3_5_scoring import parse_scores_array, compute_set_average


client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def _log(session: Session, message: str):
    session.progress_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "stage": "evaluation",
        "message": message,
    })


def evaluate_codes(session: Session) -> Session:
    """Score each code on quality criteria. Mutates session.codes in place."""
    if not session.codes:
        return session

    _log(session, f"Evaluating {len(session.codes)} codes on quality criteria...")

    codes_list = []
    for code in session.codes:
        quote_count = len(code.quote_ids)
        codes_list.append({
            "id": code.id,
            "label": code.label,
            "description": code.description,
            "group": code.group,
            "quote_count": quote_count,
        })

    prompt = f"""You are a qualitative research evaluation expert. Score each code on four criteria using a 1.0–5.0 scale (decimals allowed).

Criteria:
- coverage: How well does this code capture an important pattern in the data? Consider the quote count as a signal.
- actionability: Does this code encapsulate a single, clear concept? Lower scores for vague or compound codes.
- distinctiveness: Is this code clearly distinct from the other codes in the set? Lower scores for overlapping codes.
- relevance: Does this code accurately reflect what participants said? Consider the code label and description.

Research brief: {session.research_brief}

Codes to evaluate:
{json.dumps(codes_list, indent=2)}

Return a JSON array with one object per code:
[
  {{"id": "...", "coverage": 4.2, "actionability": 3.8, "distinctiveness": 4.0, "relevance": 4.5}},
  ...
]

Return ONLY the JSON array, no other text."""

    response = client.messages.create(
        model=MODELS["evaluation"],
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        scores_list = parse_scores_array(response.content[0].text)
        scores_by_id = {s["id"]: s for s in scores_list}

        scored_count = 0
        for code in session.codes:
            if code.id in scores_by_id:
                s = scores_by_id[code.id]
                code.scores = EvaluationScores(
                    coverage=min(5.0, max(1.0, float(s.get("coverage", 3.0)))),
                    actionability=min(5.0, max(1.0, float(s.get("actionability", 3.0)))),
                    distinctiveness=min(5.0, max(1.0, float(s.get("distinctiveness", 3.0)))),
                    relevance=min(5.0, max(1.0, float(s.get("relevance", 3.0)))),
                )
                scored_count += 1

        avg = compute_set_average(session.codes)
        _log(session, f"Scored {scored_count}/{len(session.codes)} codes. Average quality: {avg}/5.0")

        session.validation_results.code_evaluation = EvaluationSummary(
            scored=scored_count,
            total=len(session.codes),
            average_score=avg,
        )

    except Exception as e:
        _log(session, f"Code evaluation parsing failed: {e}")

    return session


def evaluate_themes(session: Session) -> Session:
    """Score each theme on quality criteria. Mutates session.themes in place."""
    if not session.themes:
        return session

    _log(session, f"Evaluating {len(session.themes)} themes on quality criteria...")

    themes_list = []
    for theme in session.themes:
        themes_list.append({
            "id": theme.id,
            "name": theme.name,
            "description": theme.description,
            "code_count": len(theme.code_ids),
            "quote_count": theme.quote_count,
            "has_literature": len(theme.literature_support) > 0,
        })

    prompt = f"""You are a qualitative research evaluation expert. Score each theme on four criteria using a 1.0–5.0 scale (decimals allowed).

Criteria:
- coverage: How comprehensively does this theme capture important patterns? Consider the number of codes and quotes it spans.
- actionability: Does this theme encapsulate a single, clear concept? Lower scores for themes that try to cover too much.
- distinctiveness: Is this theme clearly distinct from the other themes? Lower scores for overlapping or redundant themes.
- relevance: Does this theme accurately reflect the data and align with the research brief?

Research brief: {session.research_brief}

Themes to evaluate:
{json.dumps(themes_list, indent=2)}

Return a JSON array with one object per theme:
[
  {{"id": "...", "coverage": 4.2, "actionability": 3.8, "distinctiveness": 4.0, "relevance": 4.5}},
  ...
]

Return ONLY the JSON array, no other text."""

    response = client.messages.create(
        model=MODELS["evaluation"],
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        scores_list = parse_scores_array(response.content[0].text)
        scores_by_id = {s["id"]: s for s in scores_list}

        scored_count = 0
        for theme in session.themes:
            if theme.id in scores_by_id:
                s = scores_by_id[theme.id]
                theme.scores = EvaluationScores(
                    coverage=min(5.0, max(1.0, float(s.get("coverage", 3.0)))),
                    actionability=min(5.0, max(1.0, float(s.get("actionability", 3.0)))),
                    distinctiveness=min(5.0, max(1.0, float(s.get("distinctiveness", 3.0)))),
                    relevance=min(5.0, max(1.0, float(s.get("relevance", 3.0)))),
                )
                scored_count += 1

        avg = compute_set_average(session.themes)
        _log(session, f"Scored {scored_count}/{len(session.themes)} themes. Average quality: {avg}/5.0")

        session.validation_results.theme_evaluation = EvaluationSummary(
            scored=scored_count,
            total=len(session.themes),
            average_score=avg,
        )

    except Exception as e:
        _log(session, f"Theme evaluation parsing failed: {e}")

    return session
