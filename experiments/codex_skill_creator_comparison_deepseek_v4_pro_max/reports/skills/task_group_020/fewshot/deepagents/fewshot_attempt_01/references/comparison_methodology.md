 # Comparison Methodology

 ## Core Workflow

 Every M&A workbench task reduces to the same pattern:

 1. **Fetch the deal record** — headline purchase price, parties, structure
 2. **Fetch the current draft terms** — every term under `GET /api/deals/<deal_id>/terms`
 3. **Fetch the governing rules** — playbook rules or policy thresholds
 4. **Fetch supporting records** — consents, employees, regulatory, risk estimates, benchmarks, diligence findings, material contracts, notes
 5. **Compare draft against rules** — classify each mismatch
 6. **Produce structured JSON** — values computed from purchase price, ordered by priority

 ## Issue Classification

 For each term that appears in the governing rules (playbook or policy), compare the draft value against the rule. Classify:

 | Status | When |
 |---|---|
 | `in_policy` | Draft falls within playbook/policy acceptable range |
 | `out_of_policy` | Draft exceeds a policy absolute cutoff |
 | `missing_required_term` | Playbook/policy requires a term that does not appear in the draft terms at all |
 | `draft_exceeds_playbook` | Draft exceeds the playbook's fallback position on a numeric dimension (e.g., escrow percent too high, survival months too long) |
 | `draft_below_playbook` | Draft is below the playbook's fallback position on a seller-protective or buyer-protective dimension (e.g., indemnity cap too low, reverse break fee missing) |

 ### Missing Terms

 A term is missing when the playbook or policy requires an affirmative provision but no corresponding term appears in the draft terms list. This is different from a term that exists but is below threshold. For missing terms, set `source_term_ids` to an empty array and classify as `missing_required_term`.

 ### Distractor Terms

 A term in the draft is a distractor when it falls within policy, is stale, or is not relevant to the task instruction. Exclude these from the output. The answer template's `possible_issue_ids` or similar enum lists define the relevant scope.

 ## Numeric Comparison Rules

 **Dollar amounts** — Always compute from the deal's headline purchase price unless a source record explicitly states a different basis. Multiply `headline_value × percent ÷ 100`.

 **Percent points** — Compare the draft percentage directly against playbook preferred/fallback percentages. The delta is the absolute difference in percentage points.

 **Months** — Compare draft months directly against playbook preferred/fallback months. The delta is the absolute difference.

 **Delta calculation** — When the draft exceeds the fallback: `delta = |draft - fallback|`. When the draft is below the fallback: `delta = |fallback - draft|` expressed as shortfall.

 **Missing terms with dollar impact** — When a term is missing but a dollar amount is required (e.g., escrow), treat the draft as zero and compute the shortfall from the fallback.

 ## Risk Rating

 Determine risk from the quantified exposure, business criticality, and whether the issue blocks closing:

 - `HIGH` — Blocks or materially threatens closing (consent missing, regulatory clearance required, financing at risk), or quantified exposure exceeds 1% of headline value
 - `MEDIUM` — Creates meaningful economic or legal exposure but does not independently block closing
 - `LOW` — Minor deviation, notice-only requirement, or exposure below 0.1% of headline value

 ## Priority Order

 Order issues from highest to lowest negotiation priority:

 1. Issues that independently block closing (consents, HSR, financing conditions)
 2. Issues with the largest quantified delta to fallback
 3. Issues that are missing required terms (the draft provides zero protection)
 4. Issues that exceed playbook limits (the draft gives away more than the fallback)
 5. Issues below playbook (the draft gives away less protection than the fallback but something exists)

 Within each tier, rank by quantified exposure descending.

 ## Benchmark Usage

 When the task or template calls for benchmark context, fetch from `/api/deals/<deal_id>/benchmarks` and report:

 - `metric` — The benchmark metric name
 - `sample_size` — Number of comparable transactions
 - `median` — Median value in the sample
 - `upper_quartile` — 75th percentile
 - `position` — Where the draft falls relative to the distribution

## Playbook Terms Structure

 Playbook rules from `/api/playbooks/<playbook_id>/rules` provide three positions per term:

 - **Preferred** — The ideal seller/buyer position
 - **Fallback** — The minimum acceptable position after negotiation
 - **Redlines** — Non-negotiable must-have provisions

 When comparing:
 - If the draft is at or better than preferred → `in_policy`, `accept`
 - If the draft is between preferred and fallback → `draft_exceeds_playbook` or `draft_below_playbook`, `revise`
 - If the draft is worse than fallback or missing → `draft_exceeds_playbook` / `missing_required_term`, `revise` / `add`
 - If the policy has an absolute cutoff → compare against the threshold, classify as `out_of_policy`

 ## Policy Thresholds Structure

 Policy thresholds from `/api/policies/<policy_id>/thresholds` provide:

 - **Threshold values** — Absolute limits (percent, months, amount)
 - **Approved carveout groups** — Allowed exceptions
 - **Required triggers** — Mandatory provisions (e.g., fiduciary out triggers)

 Compare draft terms against policy thresholds. A term is `out_of_policy` when the draft exceeds a threshold, adds unapproved carveouts, or removes a required trigger.

 ## Recommended Actions

 Match the action to the classification:

 | Status | Recommended Action |
 |---|---|
 | `draft_exceeds_playbook` | `revise` — reduce to fallback or better |
 | `draft_below_playbook` | `revise` or `add` — raise to fallback or better |
 | `missing_required_term` | `add` — insert the required provision |
 | `out_of_policy` | `approve_with_conditions` or `reject` — seek committee approval with stated conditions, or reject outright |
 | `in_policy` | `accept` or `approve` |

 When a term is out of policy and requires committee escalation, use `approve_with_conditions` with the specific conditions that would make it acceptable, or `reject` when the deviation is fundamentally unacceptable.
