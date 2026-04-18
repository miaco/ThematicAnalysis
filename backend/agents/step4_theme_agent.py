"""
Theme Agent: Groups codes into themes, searches literature for support,
writes interpretations, performs grounding/traceability checks, and
conducts negative case analysis.
"""

import json
import os
import re
from datetime import datetime

import anthropic

from models.schemas import Session, Theme
from orchestration.pipeline_config import MODELS
from skills.step4_grounding import check_grounding


client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def _log(session: Session, message: str):
    session.progress_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "stage": "theme_generation",
        "message": message,
    })


def generate_themes(session: Session) -> Session:
    """
    1. Group codes into 3-7 themes
    2. Search literature for supporting evidence
    3. Write interpretation for each theme
    4. Grounding/traceability check
    5. Negative case analysis (find contradictory quotes)
    6. Thick description check (min 3 quotes per theme)
    """
    if not session.codes:
        _log(session, "No codes available for theme generation.")
        return session

    _log(session, f"Starting theme generation from {len(session.codes)} codes...")

    # Build codes and quotes summary
    codes_text = ""
    for code in session.codes:
        quote_examples = []
        for qid in code.quote_ids[:3]:  # Up to 3 example quotes
            for q in session.quotes:
                if q.id == qid:
                    quote_examples.append(f'  - "{q.text[:150]}..."')
                    break
        codes_text += f"\nCode: {code.label} (Group: {code.group or 'ungrouped'})\n"
        codes_text += f"  Description: {code.description}\n"
        codes_text += f"  Quote count: {len(code.quote_ids)}\n"
        if quote_examples:
            codes_text += "  Example quotes:\n" + "\n".join(quote_examples) + "\n"

    # Include all quotes for contradictory analysis
    all_quotes_text = ""
    for q in session.quotes:
        p_name = next((p.name for p in session.participants if p.id == q.participant_id), "Unknown")
        all_quotes_text += f'\nQuote ID {q.id} ({p_name}): "{q.text[:200]}"\n'

    prompt = f"""You are an expert qualitative researcher developing themes from coded data for thematic analysis.

Research Brief: {session.research_brief}

You have {len(session.codes)} codes from {len(session.quotes)} quotes across {len(session.participants)} participants.

CODES AND THEIR QUOTE EXAMPLES:
{codes_text}

ALL QUOTES (for negative case analysis):
{all_quotes_text[:6000]}

Your task is to:

1. THEME DEVELOPMENT: Group the codes into 3-7 meaningful themes that:
   - Are conceptually coherent and distinct from one another
   - Are grounded in the data (supported by multiple codes and quotes)
   - Address the research brief
   - Capture the range and complexity of participants' experiences

2. LITERATURE SUPPORT: For each theme, identify 2-4 relevant academic references or theoretical frameworks that support or contextualize the theme. Use realistic academic citations in APA format.

3. INTERPRETATION: Write a rich, nuanced interpretation (2-3 paragraphs) for each theme explaining:
   - What the theme means in context of the research brief
   - How it connects to participants' experiences
   - Its theoretical significance

4. GROUNDING CHECK: For each theme, verify the chain of evidence: theme → codes → quotes → transcripts.

5. NEGATIVE CASE ANALYSIS: For each theme, actively search for quotes that CONTRADICT or complicate the theme. List the IDs of any contradictory quotes.

6. THICK DESCRIPTION: Ensure each theme has at least 3 supporting quotes. Flag any themes with fewer.

Return a JSON object with this exact structure:
{{
  "themes": [
    {{
      "name": "Theme name",
      "description": "2-3 sentence description of the theme",
      "code_ids": ["code_label_1", "code_label_2"],
      "quote_count": 5,
      "literature_support": [
        "Author, A. (Year). Title. Journal, Vol(Issue), pages.",
        "Author, B. & Author, C. (Year). Book title. Publisher."
      ],
      "interpretation": "Rich 2-3 paragraph interpretation...",
      "contradictory_quotes": ["quote_id_1", "quote_id_2"],
      "thick_description_met": true,
      "grounding_notes": "Brief note on traceability from theme to data"
    }}
  ],
  "thematic_map_notes": "Overview of how the themes relate to each other and to the research brief",
  "data_saturation_assessment": "Assessment of whether the themes adequately cover the data"
}}

IMPORTANT: Return ONLY valid JSON, no markdown code blocks."""

    _log(session, "Calling Claude for theme generation and analysis...")

    with client.messages.stream(
        model=MODELS["primary"],
        max_tokens=12000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        final_msg = stream.get_final_message()
        full_text = ""
        for block in final_msg.content:
            if block.type == "text":
                full_text += block.text

    # Parse the JSON response
    try:
        clean = re.sub(r"```(?:json)?", "", full_text).strip().strip("`")
        data = json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', full_text, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError(f"Could not parse themes JSON: {full_text[:500]}")

    # Build Theme objects
    themes = []
    thin_themes = []

    for t_data in data.get("themes", []):
        theme_name = t_data.get("name", "Unnamed Theme")

        # Map code labels to code IDs
        code_label_refs = t_data.get("code_ids", [])
        matched_code_ids = []
        for code_ref in code_label_refs:
            for code in session.codes:
                if code.label.lower() == code_ref.lower() or code.id == code_ref:
                    matched_code_ids.append(code.id)
                    break

        # If no matches by label, try partial match
        if not matched_code_ids:
            for code_ref in code_label_refs:
                for code in session.codes:
                    if code_ref.lower() in code.label.lower():
                        matched_code_ids.append(code.id)
                        break

        # Count actual quotes for this theme's codes
        quote_ids_for_theme = set()
        for cid in matched_code_ids:
            for code in session.codes:
                if code.id == cid:
                    quote_ids_for_theme.update(code.quote_ids)

        quote_count = t_data.get("quote_count", len(quote_ids_for_theme))
        thick_ok = t_data.get("thick_description_met", True)

        if not thick_ok or quote_count < 3:
            thin_themes.append(theme_name)

        theme = Theme(
            name=theme_name,
            description=t_data.get("description", ""),
            code_ids=matched_code_ids if matched_code_ids else code_label_refs,
            quote_count=quote_count,
            literature_support=t_data.get("literature_support", []),
            interpretation=t_data.get("interpretation", ""),
            contradictory_quotes=t_data.get("contradictory_quotes", []),
        )
        themes.append(theme)

    session.themes = themes
    _log(session, f"Generated {len(themes)} themes")

    if thin_themes:
        _log(session, f"Warning: These themes have fewer than 3 supporting quotes (thin description): {', '.join(thin_themes)}")
        session.validation_results.thin_description_themes = thin_themes

    session.validation_results.thematic_map_notes = data.get("thematic_map_notes", "")
    session.validation_results.data_saturation_assessment = data.get("data_saturation_assessment", "")

    # Run grounding check
    grounding_issues = check_grounding(session.themes, session.codes, session.quotes)
    if grounding_issues:
        session.validation_results.grounding_issues = grounding_issues
        for issue in grounding_issues:
            _log(session, f"Grounding issue: {issue}")

    _log(session, "Theme generation complete.")
    return session
