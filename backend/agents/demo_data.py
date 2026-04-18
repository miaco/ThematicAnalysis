"""
Demo mode: provides realistic mock data for all pipeline stages
so the full UI flow can be tested without Anthropic API calls.
"""

import os
from datetime import datetime

from models.schemas import (
    Session, Quote, Participant, Code, Theme, POV,
    Recommendation, EvaluationScores, EvaluationSummary,
)


DEMO_MODE = os.environ.get("DEMO_MODE", "").lower() in ("1", "true", "yes")


def _log(session: Session, stage: str, message: str):
    session.progress_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "stage": stage,
        "message": message,
    })


# ── Participants ──────────────────────────────────────────────

_PARTICIPANTS = [
    Participant(id="p1", name="Sarah — Product Manager", screener_data={"role": "product manager", "experience": "5 years"}),
    Participant(id="p2", name="James — Engineer", screener_data={"role": "software engineer", "experience": "8 years"}),
    Participant(id="p3", name="Maria — Designer", screener_data={"role": "UX designer", "experience": "3 years"}),
]


# ── Quotes ────────────────────────────────────────────────────

_QUOTES = [
    Quote(id="q1", text="I feel like we're constantly context-switching between projects and it really hurts my ability to do deep work.", participant_id="p1", transcript_file="transcript1.txt", context="Discussing daily workflow challenges", codes=["context-switching", "deep-work"]),
    Quote(id="q2", text="The best ideas come when we have uninterrupted time, but that almost never happens around here.", participant_id="p2", transcript_file="transcript1.txt", context="Talking about creative process", codes=["uninterrupted-time", "creativity"]),
    Quote(id="q3", text="Meetings eat up my mornings. By the time I sit down to actually design, I'm already drained.", participant_id="p3", transcript_file="transcript2.txt", context="Describing typical workday", codes=["meeting-overload", "energy-management"]),
    Quote(id="q4", text="Our team communication is great when it's async, but the synchronous stuff — standups, reviews — feels performative.", participant_id="p2", transcript_file="transcript1.txt", context="Comparing communication styles", codes=["async-communication", "performative-meetings"]),
    Quote(id="q5", text="I wish leadership understood that shipping fast doesn't mean shipping well.", participant_id="p1", transcript_file="transcript2.txt", context="Discussing quality vs speed", codes=["quality-vs-speed", "leadership-alignment"]),
    Quote(id="q6", text="When I get into a flow state, I can accomplish more in two hours than in a full day of fragmented work.", participant_id="p3", transcript_file="transcript2.txt", context="Describing peak productivity", codes=["flow-state", "fragmented-work"]),
    Quote(id="q7", text="Documentation is the first thing that gets cut when deadlines tighten, and then we pay for it later.", participant_id="p2", transcript_file="transcript1.txt", context="Discussing technical debt", codes=["documentation", "technical-debt"]),
    Quote(id="q8", text="Cross-functional collaboration sounds great in theory, but in practice it means more meetings for everyone.", participant_id="p1", transcript_file="transcript2.txt", context="Reflecting on org structure", codes=["cross-functional", "meeting-overload"]),
]


# ── Codes ─────────────────────────────────────────────────────

_CODES = [
    Code(id="c1", label="Context-switching burden", description="Participants describe the cognitive cost of frequently shifting between tasks and projects.", quote_ids=["q1", "q6"], group="Focus & Flow", scores=EvaluationScores(coverage=4.5, actionability=4.0, distinctiveness=4.2, relevance=4.8)),
    Code(id="c2", label="Deep work deficit", description="Lack of uninterrupted time blocks for concentrated, creative work.", quote_ids=["q1", "q2", "q6"], group="Focus & Flow", scores=EvaluationScores(coverage=4.8, actionability=4.3, distinctiveness=3.9, relevance=4.6)),
    Code(id="c3", label="Meeting overload", description="Excessive synchronous meetings consume productive hours and drain energy.", quote_ids=["q3", "q4", "q8"], group="Communication Patterns", scores=EvaluationScores(coverage=4.7, actionability=4.5, distinctiveness=4.1, relevance=4.4)),
    Code(id="c4", label="Async-first preference", description="Team members express a preference for asynchronous communication over real-time meetings.", quote_ids=["q4"], group="Communication Patterns", scores=EvaluationScores(coverage=3.2, actionability=3.8, distinctiveness=4.0, relevance=4.2)),
    Code(id="c5", label="Quality-speed tension", description="Perceived conflict between organizational pressure to ship fast and desire to ship well.", quote_ids=["q5", "q7"], group="Organizational Pressure", scores=EvaluationScores(coverage=4.0, actionability=3.5, distinctiveness=4.4, relevance=4.7)),
    Code(id="c6", label="Documentation debt", description="Important documentation work is deprioritized under deadline pressure, creating long-term costs.", quote_ids=["q7"], group="Organizational Pressure", scores=EvaluationScores(coverage=3.0, actionability=4.1, distinctiveness=4.5, relevance=4.0)),
]


# ── Themes ────────────────────────────────────────────────────

_THEMES = [
    Theme(
        id="t1",
        name="The Focus Crisis",
        description="Participants consistently reported an inability to achieve sustained focus due to context-switching, meeting overload, and fragmented schedules.",
        code_ids=["c1", "c2", "c3"],
        quote_count=6,
        literature_support=[
            "Newport, C. (2016). Deep Work: Rules for Focused Success in a Distracted World. Grand Central Publishing.",
            "Mark, G., Gonzalez, V. M., & Harris, J. (2005). No task left behind? Examining the nature of fragmented work. CHI '05, 321-330.",
        ],
        interpretation="The most prominent theme across all participants was a pervasive difficulty maintaining focused, uninterrupted work time. Participants described context-switching as cognitively expensive and emotionally draining. The meeting-heavy culture was identified as the primary structural barrier to deep work, with participants noting that even well-intentioned collaboration rituals often felt 'performative' rather than productive.\n\nThis finding aligns with Newport's (2016) concept of deep work and Mark et al.'s research on fragmented work patterns. The data suggests that productivity interventions should prioritize protecting focus time over adding new collaboration touchpoints.",
        contradictory_quotes=["q8"],
        scores=EvaluationScores(coverage=4.7, actionability=4.2, distinctiveness=4.0, relevance=4.8),
    ),
    Theme(
        id="t2",
        name="Communication Mode Mismatch",
        description="There is a disconnect between the communication modes the organization defaults to (synchronous) and those that participants find most effective (asynchronous).",
        code_ids=["c3", "c4"],
        quote_count=4,
        literature_support=[
            "Rosen, C. (2008). The myth of multitasking. The New Atlantis, 20, 105-110.",
            "Perlow, L. A. (2012). Sleeping with Your Smartphone. Harvard Business Review Press.",
        ],
        interpretation="Participants expressed a clear preference for asynchronous communication, particularly for status updates and routine coordination. The synchronous-heavy defaults (daily standups, ad-hoc meetings) were perceived as interruptions rather than enablers. James's observation that async communication 'works great' while sync meetings feel 'performative' captures the sentiment well.\n\nThis theme raises questions about organizational communication norms and whether current meeting cadences serve their intended purpose or simply persist as institutional habits.",
        contradictory_quotes=[],
        scores=EvaluationScores(coverage=3.8, actionability=4.0, distinctiveness=4.3, relevance=4.1),
    ),
    Theme(
        id="t3",
        name="The Velocity Trap",
        description="The organizational emphasis on shipping speed creates hidden costs in quality, documentation, and team morale.",
        code_ids=["c5", "c6"],
        quote_count=3,
        literature_support=[
            "Forsgren, N., Humble, J., & Kim, G. (2018). Accelerate: The Science of Lean Software and DevOps. IT Revolution.",
            "Cunningham, W. (1992). The WyCash Portfolio Management System. OOPSLA '92 Experience Report.",
        ],
        interpretation="Several participants described a persistent tension between the pace of delivery demanded by leadership and the quality standards they held for their own work. This 'velocity trap' manifests concretely in deferred documentation and accumulated technical debt, which participants recognize as creating future costs.\n\nSarah's observation that 'shipping fast doesn't mean shipping well' reflects a deeper values misalignment that may affect retention and engagement over time. The literature on technical debt (Cunningham, 1992) and software delivery performance (Forsgren et al., 2018) suggests that sustainable velocity actually requires investment in quality practices.",
        contradictory_quotes=[],
        scores=EvaluationScores(coverage=3.5, actionability=3.8, distinctiveness=4.5, relevance=4.6),
    ),
]


# ── POVs ──────────────────────────────────────────────────────

_POVS = [
    POV(id="pov1", title="Protect the Maker's Schedule", description="The primary opportunity is restructuring how the team spends its time to create protected focus blocks.", rationale="Themes 1 and 2 both point to structural time management as the root issue. By establishing meeting-free blocks, async-first defaults, and explicit focus time policies, the organization can address the most frequently cited pain point. This POV centers the individual contributor's experience.", supporting_themes=["The Focus Crisis", "Communication Mode Mismatch"]),
    POV(id="pov2", title="Redefine What 'Fast' Means", description="The organization should shift from measuring output velocity to measuring sustainable delivery quality.", rationale="Theme 3 highlights that current speed metrics may be counterproductive. Combined with Theme 1's focus challenges, this POV argues that true velocity comes from quality, focus, and reduced rework — not from more hours or more pressure.", supporting_themes=["The Velocity Trap", "The Focus Crisis"]),
    POV(id="pov3", title="Communication as Infrastructure", description="Treat communication norms as deliberate organizational infrastructure rather than emergent habits.", rationale="This more systemic view foregrounds Theme 2 and argues that meeting overload (Theme 1) and quality erosion (Theme 3) are downstream effects of poorly designed communication systems. Redesigning communication defaults — when to meet, how to share status, what needs sync vs async — addresses root causes.", supporting_themes=["Communication Mode Mismatch", "The Focus Crisis", "The Velocity Trap"]),
]


# ── Recommendations ───────────────────────────────────────────

_RECOMMENDATIONS = [
    Recommendation(text="Establish 'Focus Fridays' — no-meeting days for deep work across the organization.", supporting_theme="The Focus Crisis", priority="high"),
    Recommendation(text="Replace daily standups with async written check-ins using a shared channel or tool.", supporting_theme="Communication Mode Mismatch", priority="high"),
    Recommendation(text="Introduce a 'documentation budget' — allocate 10% of each sprint to documentation work.", supporting_theme="The Velocity Trap", priority="high"),
    Recommendation(text="Audit all recurring meetings quarterly; cancel any that lack a clear decision-making purpose.", supporting_theme="The Focus Crisis", priority="high"),
    Recommendation(text="Define explicit async-first communication norms and default to async for status updates.", supporting_theme="Communication Mode Mismatch", priority="medium"),
    Recommendation(text="Create a team agreement on response-time expectations for async messages (e.g., 4-hour SLA).", supporting_theme="Communication Mode Mismatch", priority="medium"),
    Recommendation(text="Introduce 'quality gates' that include documentation checks before features ship.", supporting_theme="The Velocity Trap", priority="medium"),
    Recommendation(text="Train managers on the cognitive cost of context-switching to build empathy for maker schedules.", supporting_theme="The Focus Crisis", priority="medium"),
    Recommendation(text="Pilot a 4-day work week to test whether compressed schedules improve focus and output quality.", supporting_theme="The Focus Crisis", priority="low"),
    Recommendation(text="Establish a tech debt register that makes hidden quality costs visible to leadership.", supporting_theme="The Velocity Trap", priority="low"),
    Recommendation(text="Survey the team quarterly on communication satisfaction and focus-time availability.", supporting_theme="Communication Mode Mismatch", priority="low"),
    Recommendation(text="Create an internal 'deep work' handbook with tips and team norms for protecting focus time.", supporting_theme="The Focus Crisis", priority="low"),
]


# ── Mock report ───────────────────────────────────────────────

_DEMO_REPORT = """# Thematic Analysis: Workplace Productivity and Communication Patterns

## Executive Summary

- **Context-switching and meeting overload** are the most significant barriers to productive work
- Participants strongly prefer **asynchronous communication** over synchronous meetings for routine coordination
- A perceived **tension between delivery speed and quality** is creating hidden costs in documentation debt and team morale
- Three themes emerged: The Focus Crisis, Communication Mode Mismatch, and The Velocity Trap
- Recommendations center on protecting focus time, shifting to async-first defaults, and redefining velocity metrics

## Methodology

### Research Design
This study employed reflexive thematic analysis following Braun & Clarke's (2006) six-phase framework. Semi-structured interviews were conducted with team members across product, engineering, and design functions.

### Participants
| Participant | Role | Experience |
|---|---|---|
| Sarah | Product Manager | 5 years |
| James | Software Engineer | 8 years |
| Maria | UX Designer | 3 years |

### Data Collection
Two transcripts were analyzed, containing interviews with 3 participants. Data saturation was approached but not fully reached given the small sample size.

### Analytical Process
8 quotes were extracted and assigned to 6 open codes, which were grouped into 3 themes. Each theme was evaluated for quality using coverage, actionability, distinctiveness, and relevance criteria.

## Findings

### Theme 1: The Focus Crisis

Participants consistently reported an inability to achieve sustained focus due to context-switching, meeting overload, and fragmented schedules.

> "I feel like we're constantly context-switching between projects and it really hurts my ability to do deep work."
> — Sarah, Product Manager

> "When I get into a flow state, I can accomplish more in two hours than in a full day of fragmented work."
> — Maria, Designer

> "Meetings eat up my mornings. By the time I sit down to actually design, I'm already drained."
> — Maria, Designer

This theme aligns with Newport's (2016) concept of deep work and Mark et al.'s (2005) research on fragmented work patterns.

### Theme 2: Communication Mode Mismatch

There is a disconnect between the organization's default communication modes (synchronous) and those participants find most effective (asynchronous).

> "Our team communication is great when it's async, but the synchronous stuff — standups, reviews — feels performative."
> — James, Engineer

> "Cross-functional collaboration sounds great in theory, but in practice it means more meetings for everyone."
> — Sarah, Product Manager

### Theme 3: The Velocity Trap

The organizational emphasis on shipping speed creates hidden costs in quality, documentation, and team morale.

> "I wish leadership understood that shipping fast doesn't mean shipping well."
> — Sarah, Product Manager

> "Documentation is the first thing that gets cut when deadlines tighten, and then we pay for it later."
> — James, Engineer

## Discussion

The three themes are interconnected: meeting overload (Theme 1) stems partly from poor communication norms (Theme 2), while the pressure to ship fast (Theme 3) further squeezes the focus time that participants need. Addressing any one theme in isolation may produce limited results.

### Limitations
- Small sample size (3 participants)
- Single organization studied
- Self-reported experiences may not reflect objective time use

## Recommendations

### High Priority
1. Establish 'Focus Fridays' — no-meeting days for deep work
2. Replace daily standups with async written check-ins
3. Introduce a 'documentation budget' of 10% per sprint
4. Audit all recurring meetings quarterly

### Medium Priority
5. Define async-first communication norms
6. Create response-time expectations for async messages
7. Introduce quality gates including documentation checks
8. Train managers on the cognitive cost of context-switching

### Low Priority
9. Pilot a 4-day work week
10. Establish a tech debt register
11. Quarterly communication satisfaction surveys
12. Create an internal 'deep work' handbook

## Appendices

### Appendix A: Themes Summary
| Theme | Codes | Quotes | Key References |
|---|---|---|---|
| The Focus Crisis | 3 | 6 | Newport (2016), Mark et al. (2005) |
| Communication Mode Mismatch | 2 | 4 | Rosen (2008), Perlow (2012) |
| The Velocity Trap | 2 | 3 | Forsgren et al. (2018), Cunningham (1992) |

### Appendix B: Participant Summary
| Name | Role | Experience |
|---|---|---|
| Sarah | Product Manager | 5 years |
| James | Software Engineer | 8 years |
| Maria | UX Designer | 3 years |

### Appendix C: Code Book
| Code | Description | Frequency |
|---|---|---|
| Context-switching burden | Cognitive cost of shifting between tasks | 2 quotes |
| Deep work deficit | Lack of uninterrupted focus time | 3 quotes |
| Meeting overload | Excessive synchronous meetings | 3 quotes |
| Async-first preference | Preference for async communication | 1 quote |
| Quality-speed tension | Conflict between speed and quality | 2 quotes |
| Documentation debt | Deprioritized documentation work | 1 quote |
"""


# ── Mock agent functions ──────────────────────────────────────

def demo_analyze_transcripts(session: Session) -> Session:
    _log(session, "transcript_analysis", "[DEMO] Simulating transcript analysis...")
    session.participants = _PARTICIPANTS
    session.quotes = _QUOTES
    session.data_saturation_reached = False
    session.participant_coverage = {p.id: True for p in _PARTICIPANTS}
    _log(session, "transcript_analysis", f"[DEMO] Extracted {len(_QUOTES)} quotes from {len(_PARTICIPANTS)} participants.")
    return session


def demo_code_quotes(session: Session) -> Session:
    _log(session, "coding", "[DEMO] Simulating open coding...")
    session.codes = _CODES
    session.validation_results.coding_summary = "[DEMO] 6 codes generated across 3 groups."
    _log(session, "coding", f"[DEMO] Generated {len(_CODES)} codes.")
    return session


def demo_evaluate_codes(session: Session) -> Session:
    _log(session, "evaluation", "[DEMO] Simulating code evaluation...")
    # Scores are already baked into _CODES
    avg = round(sum(c.scores.average for c in session.codes if c.scores) / len(session.codes), 2)
    session.validation_results.code_evaluation = EvaluationSummary(
        scored=len(session.codes), total=len(session.codes), average_score=avg
    )
    _log(session, "evaluation", f"[DEMO] Scored {len(session.codes)} codes. Average: {avg}/5.0")
    return session


def demo_generate_themes(session: Session) -> Session:
    _log(session, "theme_generation", "[DEMO] Simulating theme generation...")
    session.themes = _THEMES
    _log(session, "theme_generation", f"[DEMO] Generated {len(_THEMES)} themes.")
    return session


def demo_evaluate_themes(session: Session) -> Session:
    _log(session, "evaluation", "[DEMO] Simulating theme evaluation...")
    avg = round(sum(t.scores.average for t in session.themes if t.scores) / len(session.themes), 2)
    session.validation_results.theme_evaluation = EvaluationSummary(
        scored=len(session.themes), total=len(session.themes), average_score=avg
    )
    _log(session, "evaluation", f"[DEMO] Scored {len(session.themes)} themes. Average: {avg}/5.0")
    return session


def demo_propose_povs(session: Session) -> Session:
    _log(session, "pov_generation", "[DEMO] Simulating POV generation...")
    session.povs = _POVS
    _log(session, "pov_generation", f"[DEMO] Generated {len(_POVS)} Points of View.")
    return session


def demo_generate_recommendations(session: Session) -> Session:
    _log(session, "processing_recommendations", "[DEMO] Simulating recommendation generation...")
    session.recommendations = _RECOMMENDATIONS
    _log(session, "processing_recommendations", f"[DEMO] Generated {len(_RECOMMENDATIONS)} recommendations.")
    return session


def demo_write_report(session: Session) -> Session:
    _log(session, "report_writing", "[DEMO] Generating demo report...")
    session.report = _DEMO_REPORT
    _log(session, "report_writing", f"[DEMO] Report generated ({len(_DEMO_REPORT)} chars).")
    return session
