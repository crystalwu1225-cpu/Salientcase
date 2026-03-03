# Routing Specification

Per form input, the third piece of information is routing.

## Output fields

The system outputs:
- `routing_team`
- `routing_rationale`
- `next_steps` (2–5 targeted questions)
- `escalation_flag` (`true`/`false`)

Routing is primarily based on primary bucket.
Escalation depends on severity + compliance/legal/financial/payment risk.

## Team ownership map

Use this fixed mapping:

- Infrastructure → Platform / Infra
- STT → Voice AI
- TTS → Voice AI
- LLM → Conversation AI
- Post-call → Integrations / Data

## Escalation logic

Set `escalation_flag = true` if any of the following is true:

- Severity == `Sev0`
- Severity == `Sev1`
- Compliance / legal risk detected
- Financial duplication detected
- Payment flow blocked

Otherwise set `escalation_flag = false`.

If `escalation_flag = true`, include `Exec visibility recommended` in `next_steps` while keeping total `next_steps` items to 2–5.

## Next steps (targeted questions)

Generate 2–5 concise follow-up questions based on primary bucket to unblock engineering.

### Infrastructure
- When did this start?
- Is this affecting all customers?
- Any recent deploy before issue began?
- Can you provide 2–3 example call IDs?
- Are error rates elevated across region?

### STT
- Can you share the transcript and audio snippet?
- What language/accent was used?
- Is this happening consistently?
- Was background noise present?
- Are multiple customers affected?

### TTS
- Is the issue reproducible?
- Does this happen on long calls only?
- Which voice model is being used?
- Does barge-in fail consistently?
- Is delay consistent across calls?

### LLM
- Can you share the full transcript?
- Did the correct account data load?
- Is this reproducible?
- Any recent prompt/model changes?
- Did the agent use the correct workflow/tool?

### Post-call
- Did the call complete successfully?
- Are webhooks returning success codes?
- Is CRM reachable?
- Does this affect all calls or some?
- Are duplicate records consistent or sporadic?

## Routing rationale format

Generate a one-sentence explanation.

Examples:
- "Routed to Platform due to connectivity failure."
- "Routed to Voice AI due to speech recognition mismatch."
- "Routed to Conversation AI due to reasoning failure."
- "Routed to Integrations due to CRM write failure."

## Special-case rules

- If STT error leads to incorrect escalation, still route to Voice AI (STT primary).
- If LLM threatens customer, route to Conversation AI and escalate.
- If Infrastructure outage, route to Platform and escalate.
- If duplicate financial transactions, route to Integrations and escalate.

## Clean decision tree

1. Determine primary bucket.
2. Map to routing team.
3. Check severity.
4. If `Sev0` or `Sev1`, escalate.
5. Generate bucket-specific next steps.
6. Output short rationale.
