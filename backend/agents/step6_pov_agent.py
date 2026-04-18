"""POV Agent: Proposes 3 distinct Points of View based on themes."""

import json
import os
import re
from datetime import datetime

import anthropic

from models.schemas import Session, POV
from orchestration.pipeline_config import MODELS


client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def _log(session: Session, message: str):
    session.progress_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "stage": "pov_generation",
        "message": message,
    })


def propose_povs(session: Session) -> Session:
    """
    Based on themes and their interpretation, propose exactly 3 distinct POVs.
    Each POV represents a different analytical lens or strategic direction.
    """
    if not session.themes:
        _log(session, "No themes available for POV generation.")
        return session

    _log(session, "Generating 3 distinct Points of View from themes...")

    # Build themes summary
    themes_text = ""
    for theme in session.themes:
        themes_text += f"\nTheme: {theme.name}\n"
        themes_text += f"  Description: {theme.description}\n"
        themes_text += f"  Interpretation: {theme.interpretation[:300]}...\n" if len(theme.interpretation) > 300 else f"  Interpretation: {theme.interpretation}\n"
        themes_text += f"  Quote count: {theme.quote_count}\n"
        if theme.literature_support:
            themes_text += f"  Key references: {'; '.join(theme.literature_support[:2])}\n"

    prompt = f"""You are an expert qualitative researcher presenting findings to stakeholders.

Research Brief: {session.research_brief}

The thematic analysis has identified {len(session.themes)} themes from the data.

THEMES IDENTIFIED:
{themes_text}

Your task is to propose EXACTLY 3 distinct Points of View (POVs) that represent different ways of interpreting and acting on these findings. Each POV should:

1. Represent a coherent, defensible analytical stance
2. Be genuinely distinct from the other two (different emphasis, framing, or implication)
3. Be grounded in the themes and data
4. Have clear implications for action or decision-making
5. Acknowledge which themes are central to this POV

Think of these as three different "lenses" through which to read the research:
- POV 1 might emphasize one cluster of themes
- POV 2 might foreground different themes or interpret the same themes differently
- POV 3 might take a more contrarian or nuanced stance

Return a JSON object with this exact structure:
{{
  "povs": [
    {{
      "title": "Concise, memorable POV title (5-10 words)",
      "description": "2-3 sentence clear statement of this POV's central argument",
      "rationale": "2-3 paragraph rationale explaining: (1) which themes support this POV, (2) what it emphasizes or foregrounds, (3) what it implies for action or strategy",
      "supporting_themes": ["Theme Name 1", "Theme Name 2"],
      "key_tension": "Brief description of what this POV might miss or its key limitation"
    }}
  ]
}}

IMPORTANT: Return ONLY valid JSON, no markdown code blocks. Ensure the 3 POVs are genuinely distinct and not just paraphrases of each other."""

    _log(session, "Calling Claude to generate POVs...")

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
            raise ValueError(f"Could not parse POV JSON: {full_text[:500]}")

    povs = []
    for p_data in data.get("povs", [])[:3]:  # Ensure max 3
        pov = POV(
            title=p_data.get("title", "Unnamed POV"),
            description=p_data.get("description", ""),
            rationale=p_data.get("rationale", ""),
            supporting_themes=p_data.get("supporting_themes", []),
        )
        povs.append(pov)

    session.povs = povs
    _log(session, f"Generated {len(povs)} Points of View")
    return session
