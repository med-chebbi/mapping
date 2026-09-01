"""Evidence-only status calculation."""

from __future__ import annotations

from .model import Evidence, MatchResult, Status

WEAK_KINDS = {"short-name", "element-type", "candidate-context"}


def calculate_status(candidate_count: int, evidence: tuple[Evidence, ...]) -> tuple[Status, str]:
    if candidate_count == 0:
        return Status.NOT_MAPPED, "No credible ARXML candidate was discovered."
    required = tuple(item for item in evidence if item.required)
    failures = tuple(item for item in required if item.result != MatchResult.MATCH)
    strong_matches = tuple(item for item in evidence if item.result == MatchResult.MATCH and item.kind not in WEAK_KINDS)
    ambiguity = tuple(item for item in evidence if item.result == MatchResult.AMBIGUOUS)
    if not failures and strong_matches and not ambiguity:
        return Status.MAPPED, "A unique credible ARXML structure preserves all required semantics."
    reasons: list[str] = []
    if ambiguity:
        reasons.append("candidate or reference resolution is ambiguous")
    if failures:
        reasons.append("required evidence is missing, transformed, unresolved, or mismatched")
    if not strong_matches:
        reasons.append("only supporting structural/name evidence is available")
    return Status.PARTIAL, "; ".join(reasons).capitalize() + "."
