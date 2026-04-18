"""
Skill: Check coding consistency across quotes.
"""

from collections import defaultdict

from models.schemas import Quote, CodingConsistencyIssue


def check_coding_consistency(quotes: list[Quote]) -> list[CodingConsistencyIssue]:
    """
    Find similar quotes (Jaccard similarity > 0.4) from the same transcript
    that received no overlapping codes — potential consistency issues.
    """
    issues: list[CodingConsistencyIssue] = []
    by_file: dict[str, list[Quote]] = defaultdict(list)
    for q in quotes:
        by_file[q.transcript_file].append(q)

    for filename, file_quotes in by_file.items():
        for i in range(len(file_quotes)):
            for j in range(i + 1, len(file_quotes)):
                q1, q2 = file_quotes[i], file_quotes[j]
                words1 = set(q1.text.lower().split())
                words2 = set(q2.text.lower().split())
                if not words1 or not words2:
                    continue
                intersection = words1 & words2
                union = words1 | words2
                similarity = len(intersection) / len(union)

                if similarity > 0.4:
                    codes1 = set(q1.codes)
                    codes2 = set(q2.codes)
                    if codes1 and codes2 and not codes1.intersection(codes2):
                        issues.append(CodingConsistencyIssue(
                            quote1_id=q1.id,
                            quote2_id=q2.id,
                            similarity_score=round(similarity, 2),
                            codes1=list(codes1),
                            codes2=list(codes2),
                            note="Similar quotes have no overlapping codes — consider reviewing for consistency",
                        ))

    return issues[:10]
