"""Deterministic severity tagging layer for form inputs.

This module implements the severity model defined in ``severity_model_rules.md`` and
returns standardized output fields:
- severity
- severity_rationale

It is designed to be the data-tagging layer for incoming bug report form payloads.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


SEVERITY_ORDER: Dict[str, int] = {"Sev0": 0, "Sev1": 1, "Sev2": 2, "Sev3": 3}
ALLOWED_SEVERITIES = tuple(SEVERITY_ORDER.keys())


@dataclass(frozen=True)
class SeverityInput:
    """Input payload expected from the form/classification layer."""

    impact: str
    bug_report_text: str
    primary_bucket: str


def _normalized(text: str) -> str:
    return " ".join((text or "").lower().split())


def _contains_any(text: str, phrases: List[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _max_severity(current: str, candidate: str) -> str:
    """Return the higher-priority severity (Sev0 highest)."""
    return candidate if SEVERITY_ORDER[candidate] < SEVERITY_ORDER[current] else current


def assign_severity(payload: SeverityInput) -> Dict[str, str]:
    """Assign exactly one deterministic severity and rationale.

    Returns a dictionary with:
    - ``severity``
    - ``severity_rationale``
    """

    impact = (payload.impact or "").strip()
    bucket = _normalized(payload.primary_bucket)
    text = _normalized(payload.bug_report_text)

    # STEP 1 — Hard overrides (Sev0)
    sev0_phrases = [
        "calls cannot be placed",
        "calls cannot be received",
        "cannot place or receive calls",
        "system-wide 500",
        "server errors",
        "nothing is saving across calls",
        "carrier connect rate near zero",
        "widespread recording failure",
        "widespread storage failure",
        "authentication failure preventing calls",
        "compliance-threatening systemic issue",
    ]
    if impact == "Outage" or _contains_any(text, sev0_phrases):
        return {
            "severity": "Sev0",
            "severity_rationale": (
                "Marked Sev0 due to outage-level impact with systemic business disruption "
                "across calling workflows."
            ),
        }

    # Baseline from impact (Step 3, after Sev0 check)
    if impact == "Many callers":
        severity = "Sev1"
        scope = "many callers"
    else:
        # Single caller (or unrecognized impact defaults to isolated handling)
        severity = "Sev2"
        scope = "single caller"

    # STEP 2 — Compliance/legal minimum Sev1
    compliance_phrases = [
        "agent threatens a customer",
        "arrest threat",
        "illegal claim",
        "violates policy",
        "policy violation",
    ]
    compliance_risk = _contains_any(text, compliance_phrases)
    if compliance_risk:
        severity = _max_severity(severity, "Sev1")

    # STEP 4 — Functional severity adjustments
    sev1_functional_phrases = [
        "agent loops repeatedly",
        "loops repeatedly",
        "escalates customers incorrectly",
        "blocks payment flow",
        "voice delay > 5 seconds",
        "voice delay over 5 seconds",
        "financial harm",
        "duplicate financial records",
        "post-call summaries missing for many calls",
    ]
    if _contains_any(text, sev1_functional_phrases):
        severity = _max_severity(severity, "Sev1")

    # STEP 5 — Bucket-specific modifiers
    if "infrastructure" in bucket:
        if _contains_any(text, ["system-wide failure"]):
            severity = _max_severity(severity, "Sev0")
        elif _contains_any(text, ["partial carrier degradation"]):
            severity = _max_severity(severity, "Sev1")
        elif _contains_any(text, ["isolated connect issue"]):
            severity = _max_severity(severity, "Sev2")
    elif bucket == "stt":
        if _contains_any(text, ["misinterpretation causing financial action"]):
            severity = _max_severity(severity, "Sev1")
        elif _contains_any(text, ["minor transcript inaccuracies"]):
            severity = _max_severity(severity, "Sev2")
    elif bucket == "tts":
        if _contains_any(text, ["audio unusable"]):
            severity = _max_severity(severity, "Sev1")
        elif _contains_any(text, ["noticeable delay but usable"]):
            severity = _max_severity(severity, "Sev2")
        elif _contains_any(text, ["slight pronunciation issue"]):
            severity = _max_severity(severity, "Sev3")
    elif bucket == "llm":
        if _contains_any(text, ["policy violation", "looping behavior"]):
            severity = _max_severity(severity, "Sev1")
        elif _contains_any(text, ["incorrect but recoverable answer"]):
            severity = _max_severity(severity, "Sev2")
    elif bucket in {"post-call", "post call", "postcall"}:
        if _contains_any(text, ["data not saved for many calls"]):
            severity = _max_severity(severity, "Sev1")
        elif _contains_any(text, ["single crm write failure", "duplicate log without financial impact"]):
            severity = _max_severity(severity, "Sev2")

    # Single-caller rule requested by user:
    # when no Sev0/Sev1 trigger is met, classify as Sev2 or Sev3 based on low-impact criteria.
    sev3_conditions = [
        "cosmetic issue only",
        "no business impact",
        "edge case with low frequency",
        "no customer harm",
    ]
    if impact == "Single caller" and severity not in {"Sev0", "Sev1"}:
        if all(condition in text for condition in sev3_conditions):
            severity = "Sev3"
        else:
            severity = "Sev2"

    business_impact = {
        "Sev0": "outage-level business impact",
        "Sev1": "high business risk requiring urgent mitigation",
        "Sev2": "moderate impact with localized operational disruption",
        "Sev3": "minimal impact limited to cosmetic behavior",
    }[severity]

    compliance_text = " Compliance risk identified." if compliance_risk else " No compliance risk detected."

    rationale = (
        f"Marked {severity} for impact level '{impact or 'Single caller'}' affecting {scope}; "
        f"business impact is {business_impact}. System scope is {scope}.{compliance_text}"
    )

    return {"severity": severity, "severity_rationale": rationale}


__all__ = ["SeverityInput", "assign_severity", "ALLOWED_SEVERITIES"]
