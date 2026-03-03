"""Routing logic for form inputs.

The third piece of information per form input is routing.
"""

TEAM_OWNERSHIP_MAP = {
    "Infrastructure": "Platform / Infra",
    "STT": "Voice AI",
    "TTS": "Voice AI",
    "LLM": "Conversation AI",
    "Post-call": "Integrations / Data",
}

TARGETED_QUESTIONS = {
    "Infrastructure": [
        "When did this start?",
        "Is this affecting all customers?",
        "Any recent deploy before issue began?",
        "Can you provide 2–3 example call IDs?",
        "Are error rates elevated across region?",
    ],
    "STT": [
        "Can you share the transcript and audio snippet?",
        "What language/accent was used?",
        "Is this happening consistently?",
        "Was background noise present?",
        "Are multiple customers affected?",
    ],
    "TTS": [
        "Is the issue reproducible?",
        "Does this happen on long calls only?",
        "Which voice model is being used?",
        "Does barge-in fail consistently?",
        "Is delay consistent across calls?",
    ],
    "LLM": [
        "Can you share the full transcript?",
        "Did the correct account data load?",
        "Is this reproducible?",
        "Any recent prompt/model changes?",
        "Did the agent use the correct workflow/tool?",
    ],
    "Post-call": [
        "Did the call complete successfully?",
        "Are webhooks returning success codes?",
        "Is CRM reachable?",
        "Does this affect all calls or some?",
        "Are duplicate records consistent or sporadic?",
    ],
}

RATIONALE_BY_BUCKET = {
    "Infrastructure": "Routed to Platform due to connectivity failure.",
    "STT": "Routed to Voice AI due to speech recognition mismatch.",
    "TTS": "Routed to Voice AI due to speech synthesis delivery issue.",
    "LLM": "Routed to Conversation AI due to reasoning failure.",
    "Post-call": "Routed to Integrations due to CRM write failure.",
}


def determine_routing(
    primary_bucket,
    severity,
    compliance_risk=False,
    financial_duplication=False,
    payment_flow_blocked=False,
    stt_incorrect_escalation=False,
    llm_threatens_customer=False,
    infrastructure_outage=False,
):
    """Return routing metadata based on the routing specification.

    Returns a dict with:
    - routing_team
    - routing_rationale
    - next_steps (2-5 targeted questions)
    - escalation_flag
    """
    routing_team = TEAM_OWNERSHIP_MAP.get(primary_bucket, "General Triage")

    # Special-case routing ownership
    if stt_incorrect_escalation and primary_bucket == "STT":
        routing_team = TEAM_OWNERSHIP_MAP["STT"]

    # Base escalation logic
    escalation_flag = (
        severity in {"Sev0", "Sev1"}
        or bool(compliance_risk)
        or bool(financial_duplication)
        or bool(payment_flow_blocked)
    )

    # Special-case escalation logic
    if llm_threatens_customer and primary_bucket == "LLM":
        escalation_flag = True
    if infrastructure_outage and primary_bucket == "Infrastructure":
        escalation_flag = True
    if financial_duplication and primary_bucket == "Post-call":
        escalation_flag = True

    next_steps = TARGETED_QUESTIONS.get(
        primary_bucket,
        [
            "When did this start?",
            "Is this issue reproducible?",
        ],
    )

    # Keep next_steps as 2-5 targeted items.
    next_steps = next_steps[:5]
    if len(next_steps) < 2:
        next_steps = next_steps + ["Can you share 2–3 example call IDs?"]

    if escalation_flag and "Exec visibility recommended" not in next_steps:
        next_steps.append("Exec visibility recommended")
        if len(next_steps) > 5:
            next_steps = next_steps[:4] + ["Exec visibility recommended"]

    routing_rationale = RATIONALE_BY_BUCKET.get(
        primary_bucket,
        "Routed to General Triage due to missing primary bucket mapping.",
    )

    return {
        "routing_team": routing_team,
        "routing_rationale": routing_rationale,
        "next_steps": next_steps,
        "escalation_flag": escalation_flag,
    }
