"""
Coding Agent: Open coding, validation, inter-rater reliability suggestion,
bias detection, grouping by similarity and screener questions.
"""

import json
import os
import re
from datetime import datetime

import anthropic

from models.schemas import Session, Code, InterRaterCandidate, BiasFlag
from orchestration.pipeline_config import MODELS
from skills.step2_coding_consistency import check_coding_consistency


client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def _log(session: Session, message: str):
    session.progress_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "stage": "coding",
        "message": message,
    })


def code_quotes(session: Session) -> Session:
    """
    1. Open code each quote (assign 2-4 descriptive codes)
    2. Validate coding consistency
    3. Flag inter-rater reliability candidates
    4. Detect potential bias in coding
    5. Group codes by similarity
    6. Group codes by screener questions
    """
    if not session.quotes:
        _log(session, "No quotes to code.")
        return session

    _log(session, f"Starting open coding for {len(session.quotes)} quotes...")

    # Build quotes summary for the prompt
    participant_names = {p.id: p.name for p in session.participants}
    quotes_text = ""
    for i, q in enumerate(session.quotes):
        p_name = participant_names.get(q.participant_id, "Unknown")
        quotes_text += f"\nQuote {i+1} (ID: {q.id}, Participant: {p_name}, File: {q.transcript_file}):\n\"{q.text}\"\n"

    screener_info = ""
    if session.screener_questions:
        screener_info = f"\nScreener questions: {', '.join(session.screener_questions)}"
        # Add participant screener data
        screener_info += "\nParticipant demographics:\n"
        for p in session.participants:
            screener_info += f"  {p.name}: {json.dumps(p.screener_data)}\n"

    prompt = f"""You are an expert qualitative researcher performing open coding for thematic analysis.

Research Brief: {session.research_brief}
{screener_info}

Below are {len(session.quotes)} quotes extracted from research transcripts. Your task is to:

1. OPEN CODING: Assign 2-4 descriptive, concise codes to each quote. Codes should:
   - Be descriptive and grounded in the data (use participants' own language where possible)
   - Be consistent across similar quotes
   - Capture the essence of what the quote is about

2. GROUP CODES: After coding all quotes, identify groups of similar codes that could be merged or relate to the same concept.

3. SCREENER GROUPING: For each code, note which participant groups (based on screener questions) most commonly express it.

4. BIAS DETECTION: Flag any codes that appear overly similar or that seem to reflect a pre-existing theoretical lens rather than emerging from the data.

5. INTER-RATER RELIABILITY: Flag 3-5 quotes where the coding is ambiguous and multiple interpretations are possible, to suggest for human review.

QUOTES:
{quotes_text}

Return a JSON object with this exact structure:
{{
  "codes": [
    {{
      "label": "short descriptive code label",
      "description": "1-2 sentence description of what this code captures",
      "quote_ids": ["quote_id_1", "quote_id_2"],
      "group": "similarity group name (e.g., 'emotional responses', 'barriers')",
      "screener_groups": {{
        "screener_question_1": "group_value_most_associated"
      }}
    }}
  ],
  "inter_rater_candidates": [
    {{
      "quote_id": "quote_id",
      "quote_text": "the quote text",
      "reason": "why this quote is ambiguous",
      "alternative_codes": ["code1", "code2"]
    }}
  ],
  "bias_flags": [
    {{
      "concern": "description of potential bias",
      "affected_codes": ["code1", "code2"]
    }}
  ],
  "coding_summary": "brief summary of the coding process and key patterns observed"
}}

IMPORTANT: Return ONLY valid JSON, no markdown code blocks."""

    _log(session, "Calling Claude for open coding analysis...")

    response = client.messages.create(
        model=MODELS["primary"],
        max_tokens=12000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )
    full_text = "".join(block.text for block in response.content if block.type == "text")

    # Parse the JSON response
    try:
        clean = re.sub(r"```(?:json)?", "", full_text).strip().strip("`")
        data = json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', full_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                raise ValueError(f"Could not parse coding JSON: {full_text[:500]}")
        else:
            raise ValueError(f"Could not parse coding JSON: {full_text[:500]}")

    # Build Code objects
    codes = []
    for c_data in data.get("codes", []):
        code = Code(
            label=c_data.get("label", "Unlabeled"),
            description=c_data.get("description", ""),
            quote_ids=c_data.get("quote_ids", []),
            group=c_data.get("group"),
            screener_groups=c_data.get("screener_groups", {}),
        )
        codes.append(code)

    session.codes = codes

    # Populate code labels back onto Quote objects for consistency checking
    quote_by_id = {q.id: q for q in session.quotes}
    for code in codes:
        for qid in code.quote_ids:
            if qid in quote_by_id:
                quote_by_id[qid].codes.append(code.label)

    _log(session, f"Generated {len(codes)} codes across {len(set(c.group for c in codes if c.group))} groups")

    # Store validation results
    inter_rater = data.get("inter_rater_candidates", [])
    bias_flags = data.get("bias_flags", [])

    if inter_rater:
        session.validation_results.inter_rater_candidates = [
            InterRaterCandidate(**c) for c in inter_rater
        ]
        _log(session, f"Flagged {len(inter_rater)} quotes as inter-rater reliability candidates for human review")

    if bias_flags:
        session.validation_results.bias_flags = [
            BiasFlag(**b) for b in bias_flags
        ]
        for bf in bias_flags:
            _log(session, f"Potential bias detected: {bf.get('concern', '')}")

    session.validation_results.coding_summary = data.get("coding_summary", "")

    # Validate coding consistency: check for similar quotes with very different codes
    _log(session, "Validating coding consistency...")
    consistency_issues = check_coding_consistency(session.quotes)
    if consistency_issues:
        session.validation_results.consistency_issues = consistency_issues
        _log(session, f"Found {len(consistency_issues)} potential coding consistency issues")

    _log(session, "Open coding complete.")
    return session
