"""Bug bucket classification for triage processing.

This module focuses on assigning the "Bug Bucket" tag from free-form bug reports.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

PRIORITY_ORDER = ["Infrastructure", "LLM", "STT", "TTS", "Post-call process"]


@dataclass(frozen=True)
class BugBucketClassification:
    """Result of bucket classification for a bug report."""

    primary: str | None
    secondary: str | None
    applicable: tuple[str, ...]


_BUCKET_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "Infrastructure": (
        re.compile(
            r"\b(?:"
            r"http\s*(?:error|status|code)?\s*[:=]?\s*5\d\d"
            r"|"
            r"(?:server|gateway|backend|service)\s*(?:error|status|code)?\s*[:=]?\s*5\d\d"
            r"|"
            r"5\d\d\s*(?:http\s*)?(?:error|status|response)"
            r")\b",
            re.IGNORECASE,
        ),
        re.compile(r"endpoint(s)?\s+(is\s+)?(down|failing|failed|unavailable)", re.IGNORECASE),
        re.compile(r"webhook(s)?\s+(is\s+)?(down|failing|failed).*(global|system|all)", re.IGNORECASE),
        re.compile(r"call(s)?\s+(not\s+connecting|failing\s+to\s+connect|dropping|dropped)", re.IGNORECASE),
        re.compile(r"outbound\s+(attempts?|calls?)\s+(not\s+reaching|fail(ing)?\s+to\s+reach)", re.IGNORECASE),
        re.compile(r"carrier|connect\s*rate", re.IGNORECASE),
        re.compile(r"storage\s+(failure|failed|error)", re.IGNORECASE),
        re.compile(r"recording(s)?\s+(not\s+retrievable|missing|unavailable)", re.IGNORECASE),
        re.compile(r"file\s+not\s+found", re.IGNORECASE),
        re.compile(r"database\s+write\s+(failure|failed|error)", re.IGNORECASE),
        re.compile(r"system[-\s]*wide\s+saving\s+failure", re.IGNORECASE),
        re.compile(r"authentication\s+failure|auth\s+failure", re.IGNORECASE),
    ),
    "STT": (
        re.compile(r"heard\s+\w+\s+as\s+\w+", re.IGNORECASE),
        re.compile(r"transcript\s+(does\s+not\s+match|mismatch|incorrect|wrong)", re.IGNORECASE),
        re.compile(r"transcript\s+.*(missing\s+sections?|large\s+missing)", re.IGNORECASE),
        re.compile(r"transcript\s+.*(unclear\s+markers?|inaudible\s+markers?)", re.IGNORECASE),
        re.compile(r"failed\s+to\s+understand\s+(caller'?s\s+)?language", re.IGNORECASE),
        re.compile(r"language\s+detection\s+failure", re.IGNORECASE),
        re.compile(r"accent\s+(misunderstanding|issue|problem)", re.IGNORECASE),
        re.compile(r"speaker\s+attribution\s+(incorrect|wrong|error)", re.IGNORECASE),
    ),
    "TTS": (
        re.compile(r"voice\s+sounds?\s+(unnatural|distorted)", re.IGNORECASE),
        re.compile(r"audio\s+quality\s+(is\s+)?(unclear|poor|bad)", re.IGNORECASE),
        re.compile(r"(spoken\s+response\s+delay|long\s+pause\s+before\s+speaking)", re.IGNORECASE),
        re.compile(r"speech\s+cuts?\s+off\s+mid[-\s]*sentence", re.IGNORECASE),
        re.compile(r"pronunciation\s+errors?", re.IGNORECASE),
        re.compile(r"audio\s+interrupt(ion|ed)\s+issues?", re.IGNORECASE),
        re.compile(r"voice\s+cuts?\s+off\s+when\s+interrupted", re.IGNORECASE),
    ),
    "LLM": (
        re.compile(r"repeats?\s+the\s+same\s+question", re.IGNORECASE),
        re.compile(r"loops?\s+without\s+adapting", re.IGNORECASE),
        re.compile(r"escalates?\s+incorrectly", re.IGNORECASE),
        re.compile(r"insists?\s+on\s+incorrect\s+account\s+status", re.IGNORECASE),
        re.compile(r"refuses?\s+to\s+check\s+information", re.IGNORECASE),
        re.compile(r"threatens?\s+customer", re.IGNORECASE),
        re.compile(r"makes?\s+inappropriate\s+claims", re.IGNORECASE),
        re.compile(r"uses?\s+wrong\s+workflow", re.IGNORECASE),
        re.compile(r"misuses?\s+tools?", re.IGNORECASE),
        re.compile(r"ignores?\s+provided\s+information", re.IGNORECASE),
        re.compile(r"violates?\s+policy", re.IGNORECASE),
    ),
    "Post-call process": (
        re.compile(r"summary\s+not\s+generated|missing\s+summary", re.IGNORECASE),
        re.compile(r"call\s+notes?\s+missing", re.IGNORECASE),
        re.compile(r"crm\s+not\s+updated", re.IGNORECASE),
        re.compile(r"disposition\s+code\s+missing", re.IGNORECASE),
        re.compile(r"duplicate\s+transaction\s+records?", re.IGNORECASE),
        re.compile(r"payment\s+logged\s+twice", re.IGNORECASE),
        re.compile(r"data\s+not\s+saved\s+after\s+call", re.IGNORECASE),
        re.compile(r"end[-\s]*of[-\s]*call\s+webhook\s+failed", re.IGNORECASE),
    ),
}


def _matches_any(text: str, patterns: Iterable[re.Pattern[str]]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def classify_bug(report_text: str) -> BugBucketClassification:
    """Classify a bug report into Bug Bucket tags.

    If multiple buckets are applicable, precedence is:
    Infrastructure > LLM > STT > TTS > Post-call process.
    """

    matched = [
        bucket
        for bucket in PRIORITY_ORDER
        if _matches_any(report_text, _BUCKET_PATTERNS[bucket])
    ]

    primary = matched[0] if matched else None
    secondary = matched[1] if len(matched) > 1 else None

    return BugBucketClassification(
        primary=primary,
        secondary=secondary,
        applicable=tuple(matched),
    )
