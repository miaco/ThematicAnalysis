"""
Recommendation Agent: Generates actionable recommendations
based on the selected POV and research themes.
"""

import json
import os
import re
from datetime import datetime

import anthropic

from models.schemas import Session, Recommendation
from orchestration.pipeline_config import MODELS


client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def _log(session: Session, message: str):
    session.progress_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "stage": "processing_recommendations",
        "message": message,
    })


def generate_recommendations(session: Session) -> Session:
    """
    Based on the selected POV and themes, generate 12-15 actionable recommendations.
    Each recommendation is linked to a theme with a priority level.
    """
    if not session.selected_pov:
        _log(session, "No POV selected. Cannot generate recommendations.")
        return session

    _log(session, f"Generating recommendations based on POV: '{session.selected_pov.title}'...")

    pov = session.selected_pov

    # Build context
    themes_text = ""
    for theme in session.themes:
        in_pov = theme.name in pov.supporting_themes
        marker = "★ (central to selected POV)" if in_pov else ""
        themes_text += f"\nTheme: {theme.name} {marker}\n"
        themes_text += f"  Description: {theme.description}\n"
        themes_text += f"  Interpretation: {theme.interpretation[:200]}...\n" if len(theme.interpretation) > 200 else f"  Interpretation: {theme.interpretation}\n"

    # Sample quotes for context
    sample_quotes = ""
    for q in session.quotes[:10]:
        sample_quotes += f'- "{q.text[:150]}"\n'

    prompt = f"""You are an expert qualitative researcher translating research findings into actionable recommendations.

Research Brief: {session.research_brief}

SELECTED POINT OF VIEW:
Title: {pov.title}
Description: {pov.description}
Rationale: {pov.rationale}

RESEARCH THEMES:
{themes_text}

SAMPLE PARTICIPANT QUOTES:
{sample_quotes}

Your task is to generate 12-15 specific, actionable recommendations that:
1. Flow logically from the selected POV and supporting themes
2. Are concrete and implementable (not vague platitudes)
3. Address different aspects of the research brief
4. Are prioritized by urgency and potential impact (high/medium/low)
5. Each recommendation is tied to a specific theme

For HIGH priority: Recommendations that address the most pressing needs or biggest opportunities
For MEDIUM priority: Important but not immediately urgent recommendations
For LOW priority: Valuable but longer-term or supplementary recommendations

Return a JSON object with this exact structure:
{{
  "recommendations": [
    {{
      "text": "Specific, actionable recommendation (1-2 sentences)",
      "supporting_theme": "Theme Name",
      "priority": "high",
      "rationale": "Brief (1 sentence) rationale connecting to the POV and theme"
    }}
  ],
  "implementation_notes": "Brief paragraph on how these recommendations should be prioritized and sequenced"
}}

IMPORTANT: Return ONLY valid JSON, no markdown code blocks. Aim for 12-15 recommendations with a mix of priorities (at least 3 high, 4-5 medium, 3-4 low)."""

    _log(session, "Calling Claude to generate recommendations...")

    with client.messages.stream(
        model=MODELS["primary"],
        max_tokens=6000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        final_msg = stream.get_final_message()
        full_text = ""
        for block in final_msg.content:
            if block.type == "text":
                full_text += block.text

    try:
        clean = re.sub(r"```(?:json)?", "", full_text).strip().strip("`")
        data = json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', full_text, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError(f"Could not parse recommendations JSON: {full_text[:500]}")

    recommendations = []
    for r_data in data.get("recommendations", []):
        rec = Recommendation(
            text=r_data.get("text", ""),
            supporting_theme=r_data.get("supporting_theme", ""),
            priority=r_data.get("priority", "medium").lower(),
            selected=False,
        )
        recommendations.append(rec)

    session.recommendations = recommendations
    session.validation_results.implementation_notes = data.get("implementation_notes", "")

    _log(session, f"Generated {len(recommendations)} recommendations "
                  f"({sum(1 for r in recommendations if r.priority=='high')} high, "
                  f"{sum(1 for r in recommendations if r.priority=='medium')} medium, "
                  f"{sum(1 for r in recommendations if r.priority=='low')} low priority)")
    return session
