"""
Transcript Agent: Analyzes interview transcripts to extract key quotes,
check participant coverage, detect language, and assess data saturation.
"""

import json
import os
import re
from datetime import datetime

import anthropic

from models.schemas import Session, Quote, Participant


client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def _log(session: Session, message: str):
    session.progress_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "stage": "transcript_analysis",
        "message": message,
    })


def _detect_language_and_word_count(text: str) -> dict:
    """Basic preprocessing checks."""
    words = text.split()
    word_count = len(words)
    # Simple heuristic: check for non-ASCII chars as a proxy for non-English
    ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(len(text), 1)
    language_warning = None
    if ascii_ratio < 0.7:
        language_warning = "Text may contain non-English content (high non-ASCII ratio). Please verify language."
    return {"word_count": word_count, "language_warning": language_warning}


def analyze_transcripts(session: Session) -> Session:
    """
    For each transcript:
    1. Detect language, check minimum word count
    2. Extract participant info (if identifiable)
    3. Extract key quotes relevant to the research topic
    4. Check quote accuracy
    5. Assess data saturation
    6. Check participant coverage
    """
    _log(session, f"Starting transcript analysis for {len(session.transcripts)} transcripts")

    all_quotes: list[Quote] = []
    participants_map: dict[str, Participant] = {}
    validation_results = {}

    # Preprocessing checks
    preprocessing_warnings = []
    for filename, content in session.transcripts.items():
        checks = _detect_language_and_word_count(content)
        wc = checks["word_count"]
        if wc < 100:
            preprocessing_warnings.append(
                f"{filename}: Very short transcript ({wc} words). Consider if it contains sufficient data."
            )
        if checks["language_warning"]:
            preprocessing_warnings.append(f"{filename}: {checks['language_warning']}")

    if preprocessing_warnings:
        validation_results["preprocessing_warnings"] = preprocessing_warnings
        for w in preprocessing_warnings:
            _log(session, f"Warning: {w}")

    # Build the transcript content for analysis
    transcript_content = ""
    for i, (filename, content) in enumerate(session.transcripts.items()):
        transcript_content += f"\n\n--- TRANSCRIPT {i+1}: {filename} ---\n{content[:8000]}"

    screener_info = ""
    if session.screener_questions:
        screener_info = f"\nScreener questions used: {', '.join(session.screener_questions)}"

    prompt = f"""You are an expert qualitative researcher conducting thematic analysis.

Research Brief: {session.research_brief}
{screener_info}

Below are interview transcripts. Your task is to:
1. Identify each participant (use the filename if no name is present, e.g. "Participant from transcript1.txt")
2. Extract important, verbatim quotes (minimum 3-5 per transcript) that are relevant to the research brief
3. For each quote, note the surrounding context for accuracy verification
4. Assign preliminary codes to each quote (descriptive labels for what the quote is about)
5. Extract any screener/demographic information about participants from the transcripts
6. Assess whether data saturation has been reached (are new themes/codes still emerging?)

TRANSCRIPTS:
{transcript_content}

Return a JSON object with this exact structure:
{{
  "participants": [
    {{
      "name": "Participant name or identifier",
      "transcript_file": "filename.txt",
      "screener_data": {{"age_group": "30-40", "role": "manager", ...}}
    }}
  ],
  "quotes": [
    {{
      "text": "exact verbatim quote from the transcript",
      "participant_name": "participant identifier",
      "transcript_file": "filename.txt",
      "context": "1-2 sentences surrounding the quote for accuracy checking",
      "preliminary_codes": ["code1", "code2"]
    }}
  ],
  "data_saturation_reached": false,
  "saturation_rationale": "explanation of whether new concepts are still emerging",
  "participant_coverage_notes": "notes on whether all participants are represented"
}}

IMPORTANT: Return ONLY valid JSON, no markdown code blocks, no explanation text."""

    _log(session, "Calling Claude to extract quotes and participants from transcripts...")

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        response_text = stream.get_final_message().content
        # Extract text blocks
        full_text = ""
        for block in response_text:
            if block.type == "text":
                full_text += block.text

    # Parse the JSON response
    try:
        # Strip any accidental markdown fences
        clean = re.sub(r"```(?:json)?", "", full_text).strip().strip("`")
        data = json.loads(clean)
    except json.JSONDecodeError as e:
        _log(session, f"JSON parse error: {e}. Attempting to extract JSON from response.")
        # Try to find JSON in the response
        match = re.search(r'\{.*\}', full_text, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError(f"Could not parse JSON from transcript analysis response: {full_text[:500]}")

    # Process participants
    for p_data in data.get("participants", []):
        p_name = p_data.get("name", "Unknown")
        p_id = re.sub(r'\W+', '_', p_name.lower())
        participant = Participant(
            id=p_id,
            name=p_name,
            screener_data=p_data.get("screener_data", {}),
        )
        participants_map[p_name] = participant

    session.participants = list(participants_map.values())

    # Process quotes and verify accuracy
    raw_quotes = data.get("quotes", [])
    _log(session, f"Extracted {len(raw_quotes)} quotes. Verifying accuracy...")

    verified_quotes = []
    accuracy_issues = []

    for q_data in raw_quotes:
        quote_text = q_data.get("text", "").strip()
        p_name = q_data.get("participant_name", "Unknown")
        t_file = q_data.get("transcript_file", "")
        context = q_data.get("context", "")
        codes = q_data.get("preliminary_codes", [])

        if not quote_text:
            continue

        # Accuracy check: verify the quote exists in the source transcript
        source_content = session.transcripts.get(t_file, "")
        # Normalize whitespace for comparison
        normalized_quote = " ".join(quote_text.lower().split())
        normalized_source = " ".join(source_content.lower().split())

        accuracy_ok = normalized_quote[:50] in normalized_source if len(normalized_quote) >= 10 else True

        if not accuracy_ok:
            accuracy_issues.append(f"Quote may be inaccurate: '{quote_text[:80]}...' not found verbatim in {t_file}")

        # Find participant id
        p_id = participants_map.get(p_name, Participant(name=p_name)).id

        quote = Quote(
            text=quote_text,
            participant_id=p_id,
            transcript_file=t_file,
            context=context,
            codes=codes,
        )
        verified_quotes.append(quote)

    if accuracy_issues:
        validation_results["accuracy_issues"] = accuracy_issues
        _log(session, f"Found {len(accuracy_issues)} potential accuracy issues in quotes")

    session.quotes = verified_quotes
    session.data_saturation_reached = data.get("data_saturation_reached", False)
    _log(session, f"Data saturation reached: {session.data_saturation_reached}. {data.get('saturation_rationale', '')}")

    # Participant coverage check
    participant_coverage = {}
    for participant in session.participants:
        has_quotes = any(q.participant_id == participant.id for q in session.quotes)
        participant_coverage[participant.id] = has_quotes
        if not has_quotes:
            _log(session, f"Warning: No quotes extracted for participant '{participant.name}'")

    session.participant_coverage = participant_coverage

    # Check screener group coverage (minimum 2 participants per group)
    if session.screener_questions and session.participants:
        screener_group_counts: dict[str, dict[str, int]] = {}
        for p in session.participants:
            for sq in session.screener_questions:
                key = sq.lower().replace(" ", "_")
                val = p.screener_data.get(key) or p.screener_data.get(sq, "unknown")
                if sq not in screener_group_counts:
                    screener_group_counts[sq] = {}
                screener_group_counts[sq][val] = screener_group_counts[sq].get(val, 0) + 1

        coverage_warnings = []
        for sq, groups in screener_group_counts.items():
            for group_val, count in groups.items():
                if count < 2:
                    coverage_warnings.append(
                        f"Screener group '{sq}={group_val}' has only {count} participant(s). "
                        "Minimum 2 recommended for reliable analysis."
                    )
        if coverage_warnings:
            validation_results["screener_coverage_warnings"] = coverage_warnings
            for w in coverage_warnings:
                _log(session, f"Warning: {w}")

    session.validation_results.update(validation_results)

    _log(session, f"Transcript analysis complete. {len(session.quotes)} quotes from {len(session.participants)} participants.")
    return session
