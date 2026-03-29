"""
Report Agent: Writes the complete thematic analysis report in markdown format.
Includes pre-write checks, all required sections, and appendices.
"""

import json
import os
import re
from datetime import datetime

import anthropic

from models.schemas import Session


client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def _log(session: Session, message: str):
    session.progress_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "stage": "report_writing",
        "message": message,
    })


def write_report(session: Session) -> Session:
    """
    Pre-checks, then writes the complete report.
    """
    _log(session, "Starting report generation...")

    # Pre-write checks
    issues = _run_pre_write_checks(session)
    if issues:
        for issue in issues:
            _log(session, f"Pre-write check: {issue}")
        session.validation_results["pre_write_checks"] = issues

    # Research question alignment check
    alignment_ok = _check_research_alignment(session)
    if not alignment_ok:
        _log(session, "Warning: Some themes may not clearly connect to the research brief. Review recommended.")

    # Build comprehensive context for report writing
    report_context = _build_report_context(session)

    prompt = f"""You are an expert qualitative researcher writing a comprehensive thematic analysis report.

{report_context}

Write a complete, professional thematic analysis report in markdown format. The report MUST include ALL of the following sections:

# [Report Title Based on Research Brief]

## Executive Summary
- 3-5 bullet points summarizing key findings
- Overall research purpose and scope
- Most significant insights

## Methodology
### Research Design
- Brief description of the qualitative thematic analysis approach
- Reference to Braun & Clarke (2006) thematic analysis framework where appropriate

### Participants
- Demographics table showing participant profiles (based on screener data)
- Total number of participants
- Recruitment approach (inferred from screener questions)

### Data Collection
- Description of data sources (transcripts)
- Number of transcripts analyzed
- Data saturation notes

### Analytical Process
- Description of coding process
- Number of codes generated, groups identified
- Theme development process

## Findings
For each theme, write a dedicated subsection:

### Theme 1: [Theme Name]
- Description and explanation of the theme
- Supporting evidence with at least 2 verbatim quotes (properly formatted as block quotes)
- Participant attribution for quotes
- Quote count and participant representation

[Repeat for each theme]

### Negative Cases and Contradictions
- Discuss any contradictory evidence found
- How contradictions were addressed in the analysis

## Discussion
### Interpretation and Meaning
- Synthesis of themes and what they mean together
- Connection to the selected analytical POV

### Literature Contextualization
- How findings align with or challenge existing literature
- References to theoretical frameworks

### Limitations
- Methodological limitations
- Scope limitations

## Recommendations
[List all selected recommendations, organized by priority]

### High Priority
[High priority recommendations with rationale]

### Medium Priority
[Medium priority recommendations]

### Low Priority
[Lower priority, longer-term recommendations]

## Appendices

### Appendix A: Themes Summary Table
Create a markdown table with columns:
| Theme | Codes | Quote Count | Key References |

### Appendix B: Participant Summary Table
Create a markdown table with participant demographics.

### Appendix C: Code Book
List all codes with descriptions and frequency counts.

---

IMPORTANT STYLE GUIDELINES:
- Use proper markdown formatting throughout
- Format direct quotes as > blockquotes
- Attribute quotes to participants (e.g., "Participant 3, Manager")
- Be analytical and interpretive, not just descriptive
- Maintain academic tone while being accessible to a professional audience
- Total length should be comprehensive — at least 3,000 words"""

    _log(session, "Calling Claude to write the full report...")

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        final_msg = stream.get_final_message()
        report_text = ""
        for block in final_msg.content:
            if block.type == "text":
                report_text += block.text

    session.report = report_text
    _log(session, f"Report written successfully ({len(report_text)} characters, approx {len(report_text.split())} words)")
    return session


def _run_pre_write_checks(session: Session) -> list[str]:
    """Run pre-write validation checks."""
    issues = []

    if not session.research_brief or len(session.research_brief.strip()) < 20:
        issues.append("Research brief is very short or missing. Report quality may be limited.")

    if not session.transcripts:
        issues.append("No transcript data available for the report.")

    if not session.quotes:
        issues.append("No quotes available — report will lack data evidence.")
    elif len(session.quotes) < 5:
        issues.append(f"Only {len(session.quotes)} quotes available. A richer dataset is recommended.")

    if not session.themes:
        issues.append("No themes generated — report cannot include findings section.")
    elif len(session.themes) < 2:
        issues.append(f"Only {len(session.themes)} theme(s) found. Consider whether the analysis is complete.")

    if not session.selected_pov:
        issues.append("No POV selected — report will not have a clear analytical perspective.")

    selected_recs = [r for r in session.recommendations if r.selected]
    if not selected_recs:
        issues.append("No recommendations selected — recommendations section will be empty.")
    elif len(selected_recs) < 3:
        issues.append(f"Only {len(selected_recs)} recommendation(s) selected. Consider selecting more.")

    if not session.participants:
        issues.append("No participant data — methodology section will be limited.")

    return issues


def _check_research_alignment(session: Session) -> bool:
    """
    Check that all themes connect back to the research brief.
    Simple keyword overlap check.
    """
    if not session.research_brief or not session.themes:
        return True

    brief_words = set(session.research_brief.lower().split())
    # Remove common stop words
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
                  "of", "with", "by", "from", "this", "that", "these", "those", "is",
                  "are", "was", "were", "be", "been", "being", "have", "has", "had",
                  "do", "does", "did", "will", "would", "could", "should", "may", "might"}
    brief_keywords = brief_words - stop_words

    misaligned = []
    for theme in session.themes:
        theme_words = set((theme.name + " " + theme.description).lower().split()) - stop_words
        overlap = theme_words & brief_keywords
        if len(overlap) < 2:
            misaligned.append(theme.name)

    if misaligned:
        session.validation_results["research_alignment_warnings"] = (
            f"These themes may not clearly connect to the research brief: {', '.join(misaligned)}"
        )
        return False

    return True


def _build_report_context(session: Session) -> str:
    """Build the context block for the report-writing prompt."""
    context = f"RESEARCH BRIEF:\n{session.research_brief}\n\n"

    # Selected POV
    if session.selected_pov:
        context += f"SELECTED ANALYTICAL POV:\n"
        context += f"Title: {session.selected_pov.title}\n"
        context += f"Description: {session.selected_pov.description}\n"
        context += f"Rationale: {session.selected_pov.rationale}\n\n"

    # Participants
    context += f"PARTICIPANTS ({len(session.participants)} total):\n"
    for p in session.participants:
        context += f"  - {p.name}: {json.dumps(p.screener_data)}\n"
    context += "\n"

    # Themes with full details
    context += f"THEMES ({len(session.themes)} identified):\n"
    for theme in session.themes:
        context += f"\nTheme: {theme.name}\n"
        context += f"Description: {theme.description}\n"
        context += f"Interpretation: {theme.interpretation}\n"
        context += f"Quote count: {theme.quote_count}\n"
        context += f"Literature: {'; '.join(theme.literature_support)}\n"
        if theme.contradictory_quotes:
            context += f"Contradictory quotes: {', '.join(theme.contradictory_quotes)}\n"

    # Quotes (all of them for attribution)
    context += f"\nALL QUOTES WITH PARTICIPANT ATTRIBUTION ({len(session.quotes)} total):\n"
    for q in session.quotes:
        p_name = next((p.name for p in session.participants if p.id == q.participant_id), "Unknown participant")
        p_screener = next((p.screener_data for p in session.participants if p.id == q.participant_id), {})
        role = p_screener.get("role") or p_screener.get("job_title") or p_screener.get("occupation", "")
        attribution = f"{p_name}" + (f", {role}" if role else "")
        context += f'\nQuote ID {q.id} ({attribution}): "{q.text}"\n'

    # Selected recommendations
    selected_recs = [r for r in session.recommendations if r.selected]
    if selected_recs:
        context += f"\nSELECTED RECOMMENDATIONS ({len(selected_recs)}):\n"
        for r in selected_recs:
            context += f"  [{r.priority.upper()}] {r.text} (Theme: {r.supporting_theme})\n"

    # Validation results / additional context
    if session.validation_results.get("implementation_notes"):
        context += f"\nIMPLEMENTATION NOTES: {session.validation_results['implementation_notes']}\n"

    return context
