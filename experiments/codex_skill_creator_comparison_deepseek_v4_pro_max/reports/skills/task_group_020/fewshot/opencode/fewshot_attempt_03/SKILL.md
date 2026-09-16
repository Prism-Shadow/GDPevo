---
name: deal-workbench
description: Prepare structured M&A deliverables — issue registers, economics packages, committee escalation memos, transition reviews, and deviation matrices — from a deal workbench API. Use when the user asks for M&A work, deal analysis, contract/term comparison against a playbook or policy, closing readiness assessment, indemnity/escrow/survival review, regulatory (HSR) checks, employee continuity analysis, or any structured deliverable tied to a deal workbench. Use whenever the prompt mentions a deal ID, playbook, policy thresholds, committee escalation, APA/SPA terms, or asks you to produce a JSON deliverable from deal data.
---

# Deal Workbench Skill

Prepare structured M&A deliverables using a deal workbench REST API and optional read-only SQL.

## Workflow

Follow this sequence, adapting to the specific deliverable type requested:

### Phase 1: Orient

1. **Read the answer template** — the prompt always includes `input/payloads/answer_template.json`. Read it first. It defines the exact output schema, stable enums, stable field IDs, and data type conventions. Everything you produce must fit this shape exactly.

2. **Identify the deliverable type** from the template and prompt. Common types:
   - **Issue register**: compare draft terms against a playbook (seller or buyer), produce ranked issues with quantified deltas and summary metrics.
   - **Economics/closing package**: build holder-level consideration allocation, indemnity/escrow/survival/NWC mechanics, consent and material-contract conditions, regulatory status, employee covenants, D&O tail, and closing readiness.
   - **Committee escalation**: filter to only out-of-policy terms that require committee approval, compare against policy thresholds with benchmark support, provide recommendations and required conditions with aggregate exposure totals.
   - **Transition review**: focus on carveout transition and separation terms — IP transition, trademark/domain redirects, TSA scope/fees, Section 1060 allocation, transfer taxes, employee continuity, outside-date extensions, governing law/forum.
   - **Deviation matrix**: produce a buyer-side position matrix covering indemnity caps/baskets, survival/knowledge qualifiers, materiality scrape, escrow/holdbacks, consent conditions, HSR, and material-contract blockers with closing-blocker and risk-total summaries.

### Phase 2: Pull deal data in parallel

Pull these endpoints simultaneously to reduce roundtrips. The `deal_id` comes from the prompt. The pattern is always `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/<resource>`.

**Always pull:**
- Deal record: `/api/deals/<deal_id>`
- Draft terms: `/api/deals/<deal_id>/terms`
- Playbook or policy rules (the prompt names the playbook/policy ID):
  - Playbook: `/api/playbooks/<playbook_id>/rules`
  - Policy: `/api/policies/<policy_id>/thresholds`

**Pull based on deliverable type:**
- `risk-estimates` — for issue registers, committee escalation, deviation matrices
- `benchmarks` — for issue registers, committee escalation, deviation matrices
- `notes` — negotiation notes for any deliverable
- `consents` — for economics packages, transition reviews, deviation matrices
- `employees` — for issue registers, economics packages, transition reviews
- `regulatory` — for all deliverables that involve HSR/closing conditions
- `cap-table` — for economics packages (holder allocation)
- `material-contracts` — for economics packages, transition reviews, deviation matrices
- `diligence-findings` — for economics packages, deviation matrices
- `documents` — for transition reviews (check draft doc for missing terms)

See [references/api-endpoints.md](references/api-endpoints.md) for the full API catalog.

### Phase 3: Cross-reference with read-only SQL (when available)

If the environment provides `POST /api/query` with token `deal-workbench-readonly`, use it for cross-table verification: confirm term-to-finding linkage, validate employee counts, verify consent statuses, and cross-check risk estimate IDs against findings. The SQL endpoint accepts a single SELECT or WITH statement in `{"token": "deal-workbench-readonly", "sql": "<statement>"}`.

### Phase 4: Compare draft against playbook or policy

This is the core of every deliverable. The logic depends on your side:

**Seller-side playbook comparison (APA):**
- For each playbook rule: check whether the draft has a corresponding term.
- If the draft has a term that exceeds the playbook's preferred or fallback threshold → `draft_exceeds_playbook`. Recommend `revise` to at least the fallback.
- If the draft has a term below the playbook's preferred or fallback threshold → `draft_below_playbook`. Recommend `add` or `revise`.
- If the draft is silent on a playbook-required provision → `missing_required_term`. Only flag this when the surrounding deal data (employees, regulatory, deal structure) shows the term is actually needed for this deal. Do not flag a playbook rule that is irrelevant to the specific deal context.
- If the draft matches or is within playbook bounds → `in_policy`. Exclude from issue register unless the template requires otherwise.

**Buyer-side playbook comparison (SPA):**
- Same logic, but thresholds go the opposite direction. A buyer typically wants higher indemnity caps, longer survival, tighter consents. `draft_below_playbook` means the draft is weaker than the buyer's playbook minimums.

**Policy-based escalation:**
- Compare each draft term against the policy thresholds.
- Only escalate terms that are out of policy. Exclude in-policy terms, stale terms, and distractor/non-committee terms.
- For each escalated term: provide the policy comparison, quantified amounts, benchmark support where applicable, legal/business deviation, recommendation, and required conditions.

### Phase 5: Calculate amounts

**The purchase price base is always the headline purchase price** from the deal record unless a source explicitly states a different basis.

- `draft_amount_dollars = headline_value * draft_percent / 100`
- `preferred_amount_dollars = headline_value * playbook_preferred_percent / 100`
- `fallback_amount_dollars = headline_value * playbook_fallback_percent / 100`
- `delta_to_fallback_dollars = draft_amount_dollars - fallback_amount_dollars` (for `draft_exceeds_playbook`) or `fallback_amount_dollars - draft_amount_dollars` (for `draft_below_playbook`)

**Data type conventions** — the answer template specifies precision; when it does not, use these defaults:
- Currency amounts: integer dollars (no cents)
- Percent points: two decimal places unless the template says otherwise
- Months: integers
- Dates: `YYYY-MM-DD`
- Holder percentages: four decimals when applicable

### Phase 6: Classify and rank

Use the enums from the answer template exactly. Never invent new enum values.

**Priority ordering:**
- Put issues that block closing first (financing conditions, HSR, consent conditions)
- Then issues with the largest dollar deltas
- Then issues where the playbook position is non-negotiable
- Within a tier, prefer `draft_exceeds_playbook` / `draft_below_playbook` over `missing_required_term` unless the missing term creates closing risk

**Risk rating:**
- `HIGH`: closing certainty risk, large dollar exposure, or non-negotiable playbook breach
- `MEDIUM`: moderate dollar exposure or secondary playbook deviation
- `LOW`: minor deviations or housekeeping items

### Phase 7: Assemble the JSON

Follow the answer template's shape exactly:
- Stable issue/term/consent/contract IDs must come from the workbench data, never fabricated.
- When the template provides a `possible_issue_ids` or `stable_issue_ids` list, use only those IDs.
- `source_term_ids` is an empty array `[]` for missing required terms, never `null`.
- Required boolean fields must be `true` or `false`, never `null` unless the template explicitly allows null for that field.
- Summary metrics must be internally consistent: counts must match the register length, dollar totals must sum correctly, risk counts must tally.

### Phase 8: Return only JSON

Do not include explanatory prose, markdown headers, or narrative outside the JSON object. The entire response must be a single valid JSON value (object or array as the template dictates).

## Common patterns across deliverables

### Consent and material-contract analysis
- Read `/api/deals/<deal_id>/consents` and `/api/deals/<deal_id>/material-contracts`
- Classify each consent as `closing_condition`, `notice_only`, or `post_closing_covenant` based on the consent record's type and risk
- Required closing consents are those flagged as closing conditions with HIGH risk or material revenue at stake
- Notice-only items go into a `non_blocking_notices` list
- Material contracts that require counterparty consent for change of control become closing conditions

### Employee continuity
- Read `/api/deals/<deal_id>/employees`
- Identify employees flagged for service-credit requirements
- Total PTO liability from the employee records
- WARN Act risk: employees in jurisdictions with WARN triggers
- For carveout/APA deals: identify the transferred employee group and scope the continuity requirements to that group

### HSR and regulatory
- Read `/api/deals/<deal_id>/regulatory`
- If HSR applies, an HSR clearance closing condition is always required
- `hell_or_high_water` status comes from the regulatory record or playbook
- Regulatory effort standard (`reasonable_best_efforts`, `reasonable_best_efforts_with_remedy_cap`, etc.) comes from the regulatory record

### Indemnity package (buyer-side SPA)
- Extract draft cap percentage, survival months, and materiality-scrape language from terms
- Compare against playbook preferred and fallback percentages
- Escrow: calculate as percentage of purchase price; release tied to general rep survival expiration
- NWC adjustment: dollar-for-dollar outside collar is standard buyer position

### Transition and carveout terms (seller-side APA)
- TSA: compare draft duration and fee model against playbook; flag stranded costs
- IP transition: check for trademark license and domain redirect provisions
- Section 1060: mutual agreement requirement for purchase price allocation
- Transfer taxes: 50/50 split is standard unless state law dictates otherwise
- Outside date: include seller-friendly regulatory extension right when HSR is required

## Tips

- The answer template is authoritative. When in doubt about a field's type, presence, or enum values, re-read the template.
- Empty arrays vs null: when the template says "array of X", use `[]` not `null` for the empty case. When the template says "X or null", use `null` when not applicable.
- Dollar calculations that produce fractions: round to the nearest integer dollar.
- Read the deal notes even when not explicitly asked — they often contain context about which terms are actively negotiated.
- When SQL is available, use it to verify that counts and IDs are consistent across tables. For example, verify employee counts from the employees endpoint match the deal-level employee count, or confirm that a finding ID from diligence-findings is linked to the correct term.

## Reference

- [API Endpoints Catalog](references/api-endpoints.md) — complete list of workbench API routes with descriptions
