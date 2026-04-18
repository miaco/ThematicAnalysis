"""
Skill: Evaluation scoring — parse LLM score output and compute averages.
"""

import json
import re


def parse_scores_array(text: str) -> list[dict]:
    """Extract a JSON array of score objects from LLM output."""
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return []


def compute_set_average(items) -> float:
    """Compute the mean quality score across all items that have scores."""
    scored = [item for item in items if item.scores is not None]
    if not scored:
        return 0.0
    total = sum(item.scores.average for item in scored)
    return round(total / len(scored), 2)
