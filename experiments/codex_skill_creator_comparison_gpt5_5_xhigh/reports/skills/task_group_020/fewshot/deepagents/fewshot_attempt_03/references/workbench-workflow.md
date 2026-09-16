# Workbench Workflow Reference

## Endpoint Map

Start from the prompt's `TASK_ENV_BASE_URL` and exact `deal_id`. Common routes:

- `/api/deals/<deal_id>` for deal metadata, value basis, parties, dates, client side, playbook, and policy identifiers.
- `/api/deals/<deal_id>/terms` for current draft terms, term IDs, categories, clause references, draft values, and draft silence.
- `/api/playbooks/<playbook_id>/rules` for buyer or seller required positions, preferred and fallback thresholds, missing-term requirements, and action language.
- `/api/policies/<policy_id>/thresholds` for committee approval limits, restricted terms, and routing rules.
- `/api/deals/<deal_id>/benchmarks` for market medians, quartiles, sample size, and support for whether a draft is market.
- `/api/deals/<deal_id>/risk-estimates` for modeled low/high exposure values and source estimate IDs.
- `/api/deals/<deal_id>/cap-table` for holder allocation, fully diluted percentages, security classes, and as-converted shares.
- `/api/deals/<deal_id>/consents` for required closing consents, notice-only items, post-closing covenants, amount at risk, and consent IDs.
- `/api/deals/<deal_id>/material-contracts` for material contract consent requirements, annual revenue, and blocking contracts.
- `/api/deals/<deal_id>/regulatory` for HSR requirement, industry review, clearance status, outside date implications, and remedy covenant.
- `/api/deals/<deal_id>/employees` for continuing employee counts, service credit, PTO liability, retention, WARN risk, and affected groups.
- `/api/deals/<deal_id>/diligence-findings` for NWC issues, privacy/special indemnity items, transition disruption, customer concentration, and other fact support.
- `/api/deals/<deal_id>/documents` and `/api/deals/<deal_id>/notes` for draft silence, stale/non-current terms, negotiation notes, and special instructions.

Use `POST /api/query` only for read-only cross-checks when available and scoped to the same deal. Do not use reseed or admin endpoints while solving.

## Classification Rules

Use the template's enums exactly. General classification:

- `missing_required_term`: no current draft term covers a provision required by the playbook, policy, or deal facts.
- `draft_below_playbook`: the draft gives the client less protection or economics than the client-side playbook fallback.
- `draft_exceeds_playbook`: the draft imposes more exposure, delay, optionality, or operational burden on the client than the client-side playbook allows.
- `out_of_policy`: a term breaches committee or policy thresholds, or the template uses policy status instead of above/below playbook language.
- `in_policy`: the current draft meets the requested threshold and the template asks to include accepted items.

For buyer-side work, lower caps, shorter survival, missing escrows, missing closing conditions, missing HSR conditions, missing materiality scrape, and weak consent protections usually fall below the buyer playbook. For seller-side work, buyer financing optionality, excessive escrow/cap/survival, broad termination rights, open-ended TSA obligations, buyer cherry-picking employees, missing seller tax/forum protections, and missing transition boundaries usually exceed or fail the seller playbook.

Committee escalation tasks are narrower: include only current terms that are out of policy or restricted for approval. Exclude stale, in-policy, non-committee, and wrong-deal records, listing them only when the template has exclusion fields.

## Missing-Term Detection

Do not assume every common M&A topic is an issue. Mark a missing provision only when supported by at least one source:

- Playbook or policy says the term is mandatory or fallback-required.
- Regulatory records show HSR or other approval is required but the draft lacks a clearance condition or outside-date protection.
- Consent or material-contract records show required closing consents but the draft omits or under-scopes closing conditions.
- Employee records show continuing employees, PTO liability, service-credit needs, retention/WARN issues, or field operations continuity requirements.
- Diligence findings show NWC, privacy, customer concentration, transition disruption, stranded costs, special indemnity, or similar quantified findings.
- Documents or notes show draft silence, unresolved agent/release mechanics, or a required business position.

Use empty `source_term_ids` for missing terms and put supporting non-term IDs in fields such as `source_record_ids`, blocker IDs, finding IDs, consent IDs, or note/document IDs when the template provides them.

## Calculations

Read the basis before calculating. Common bases are headline purchase price, equity value, upfront cash, identified findings, or annual revenue. If the prompt says to calculate from headline value unless another basis is explicit, use the headline value.

Formulas:

- Percent amount: `round_to_integer(basis * percent_points / 100)`.
- Buyer shortfall to fallback: `fallback_amount - draft_amount` when the draft is below fallback.
- Buyer shortfall to preferred: `preferred_amount - draft_amount` when requested.
- Seller delta to fallback: `draft_amount - fallback_amount` when the draft exceeds seller fallback.
- Fee shortfall: `required_fee_amount - draft_fee_amount`.
- Excess months over fallback: `draft_months - fallback_months`.
- Holder allocation: multiply each holder's fully diluted percentage by each consideration component; total equals cash plus stock plus milestone when the template requests it.
- Closing consent amount at risk: sum only required closing consent records, not notices or post-closing covenants.
- Material contract revenue conditioned: sum annual revenue only for material contracts that require a closing condition or consent in the template.
- Issue counts: count the emitted matrix/register items. Deviation counts usually include all non-`in_policy` statuses unless the template defines a narrower metric.

Keep percentages as JSON numbers. Trailing zero formatting is not meaningful in JSON, so use the correct numeric precision without converting numbers to strings.

## Risk, Priority, and Blockers

Prefer explicit risk ratings and modeled exposure from workbench records. If a template requires a risk rating but records give only facts, use a conservative legal priority:

- HIGH: closing certainty, required consent failure, HSR/clearance, financing optionality, material contract blocker, large cap/escrow/fee delta, employee transition disruption, open-ended transition service burden, or high quantified exposure.
- MEDIUM: survival period, tax allocation, governing law/forum, materiality scrape fallback, D&O tail amount, or manageable missing mechanics.
- LOW: notices, low-dollar consents, accepted fallback positions, or cleanups with limited closing impact.

Closing blockers usually include required consents, required regulatory clearance, and specific material-contract consents. Exclude notice-only, post-closing, accepted, stale, and non-material records unless the template asks for tradeable or non-blocking items.

Priority order should reflect negotiation consequence, not alphabetic order, unless the template requires sorting. Start with blockers to closing, then regulatory, then economics/indemnity, then employees and transition operations, then tax/forum/document mechanics.

## Final JSON Assembly

Before answering:

1. Validate every enum value against the template.
2. Ensure every required top-level key is present.
3. Ensure arrays contain objects in the requested order.
4. Ensure missing values are `null`, empty arrays, or empty objects only when the template permits them.
5. Recompute summary totals from the emitted detail rows and source records.
6. Remove all explanatory prose outside the JSON.
