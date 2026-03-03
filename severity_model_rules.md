# Severity Model (4 Levels)

## Data tags
- `data_tag_1`: primary classification bucket
- `data_tag_2`: severity

Allowed severity values:
- `Sev0`
- `Sev1`
- `Sev2`
- `Sev3`

The system must:
1. Assign exactly one severity.
2. Provide `severity_rationale`.
3. Follow deterministic rules.

## Input signals
- Impact dropdown: `Single caller` | `Many callers` | `Outage`
- Bug report text
- Primary bucket

## Deterministic rules

### Step 1 — Hard overrides (highest priority)
Assign `Sev0` if **any** are true:
- Impact dropdown = `Outage`
- Calls cannot be placed or received
- System-wide 500/server errors
- Nothing is saving across calls
- Carrier connect rate near zero
- Widespread recording/storage failure
- Authentication failure preventing calls
- Compliance-threatening systemic issue affecting multiple customers

This step overrides all other logic.

### Step 2 — Compliance / legal risk
Assign **at least** `Sev1` if any are true:
- Agent threatens a customer
- Agent makes illegal claims (for example, arrest threats)
- Agent violates policy in live customer interaction

Even when impact = `Single caller`, do **not** downgrade below `Sev1`.

### Step 3 — Impact-based scaling (if not Sev0)
- If impact = `Many callers`, minimum severity = `Sev1`
- If impact = `Single caller`, default severity = `Sev2`

### Step 4 — Functional severity adjustments
Escalate to `Sev1` if any are true:
- Agent loops repeatedly
- Agent escalates customers incorrectly
- Agent blocks payment flow
- Voice delay > 5 seconds consistently
- Misinterpretation causes financial harm
- Duplicate financial records created
- Post-call summaries missing for many calls

Keep as `Sev2` if:
- Issue is intermittent
- Workaround exists
- Affects subset of calls
- Cosmetic voice issue
- Minor pronunciation issue without business impact

Assign `Sev3` only if all are true:
- Cosmetic issue only
- No business impact
- Edge case with low frequency
- No customer harm

### Step 5 — Bucket-specific modifiers
#### Infrastructure
- System-wide failure → `Sev0`
- Partial carrier degradation → `Sev1`
- Isolated connect issue → `Sev2`

#### STT
- Misinterpretation causing financial action → `Sev1`
- Minor transcript inaccuracies → `Sev2`

#### TTS
- Audio unusable → `Sev1`
- Noticeable delay but usable → `Sev2`
- Slight pronunciation issue → `Sev3`

#### LLM
- Policy violation → `Sev1`
- Looping behavior → `Sev1`
- Incorrect but recoverable answer → `Sev2`

#### Post-call
- Data not saved for many calls → `Sev1`
- Single CRM write failure → `Sev2`
- Duplicate log without financial impact → `Sev2`

## Final priority order
When rules conflict, use the highest severity triggered:
`Sev0` > `Sev1` > `Sev2` > `Sev3`

Never downgrade below the minimum required by:
- Impact dropdown
- Compliance rule

## Required output format
The system output must include:
- `severity`
- `severity_rationale`

Rationale must reference:
- Impact level
- Business impact
- System scope
- Compliance risk (if applicable)

Example rationales:
- "Marked Sev0 due to outage-level system failure."
- "Marked Sev1 due to policy violation affecting live customer."
- "Marked Sev2 due to isolated issue affecting single caller."
- "Marked Sev3 due to cosmetic issue with no business impact."
