# Analysis Method

Reusable method for producing an M&A deal-review JSON deliverable from the workbench. The deliverable shape varies (issue register, closing/economics package, committee escalation, carveout transition review, SPA deviation matrix), but the method is the same.

## 1. Extract task parameters from the prompt
- `deal_id` — exact value; use it for every workbench query.
- `client_side` — buyer or seller. This drives which playbook/policy applies and which direction "exceeds"/"below" cuts.
- deliverable type and required coverage (the prompt enumerates what the package must cover).
- the playbook or policy id to compare against. Read the exact id from the prompt.
- unit/precision rules stated in the prompt (see `output_contract.md`).

## 2. Pull the records (by exact deal_id)
Record types you will commonly need and what each contributes:
- **deal record** — headline purchase price / equity value (the quantification base), client/counterparty, signing/meeting dates.
- **draft terms** — the current draft positions to classify; each carries a stable term_id.
- **playbook rules** — preferred and fallback positions per issue category; the comparison baseline.
- **policy thresholds** — committee policy limits (for escalation tasks).
- **risk estimates** — quantified low/high exposure bands per issue or category, each with a stable estimate id.
- **employees** — continuing-employee count, service-credit employees, PTO liability, WARN risk.
- **consents** — change-of-control/assignment consents; classify as closing_condition / notice_only / post_closing_covenant.
- **material contracts** — contracts with change-of-control provisions and annual revenue at risk.
- **regulatory** — HSR requirement, threshold basis, hell-or-high-water, effort covenants.
- **benchmarks** — median / upper-quartile market data per metric, with sample size.
- **diligence findings** — specific quantified findings (e.g., privacy, special indemnity) with stable finding ids.
- **cap table** — holder-level fully-diluted shares for consideration allocation.
- **documents** — draft document refs (e.g., governing-law/forum presence).
- **notes** — negotiation context that can sharpen priority.

## 3. Classify each relevant term
Compare each draft term (and each required-but-absent term) against the playbook/policy. Assign:
- **`issue_status`** — `in_policy`, `out_of_policy`, `missing_required_term`, `draft_exceeds_playbook`, `draft_below_playbook`.
  Direction depends on `client_side`: a term that is too buyer-favorable may be `draft_exceeds_playbook` for the seller and `draft_below_playbook` for the buyer. Apply the side's perspective.
- **`risk_rating`** — `LOW` / `MEDIUM` / `HIGH` (from risk estimates and severity).
- **`recommended_action`** (and `redline_action` where the template has redlines) — `delete` / `revise` / `add` / `accept` / `escalate` / `approve` / `approve_with_conditions` / `reject` (redlines use `add` / `delete` / `revise`).

Derive the **allowed enum values** from THIS task's `answer_template.json`; templates differ, so do not carry enums over from another task.

## 4. Missing terms and distractors
- Treat a missing or silent term as an issue (`missing_required_term`, action `add`) when the client's position requires an affirmative provision (e.g., governing law/forum, Section 1060 allocation, transfer-tax split, HSR condition, escrow, transition services, restrictive covenants).
- Exclude stale, in-policy, or non-relevant distractor terms **only when the task says to** (e.g., a committee-escalation task excludes in-policy terms; a deviation matrix may `accept` an in-policy term rather than drop it). When excluded, surface them in the template's "excluded" fields if it defines them.

## 5. Quantify from the purchase-price base
- Compute dollar amounts from the deal's headline purchase price (or equity value) **unless a source explicitly states a different basis**. percent → dollars = percent × base.
- Playbooks define **preferred** and **fallback** positions. Quantify the draft against both; compute the delta to fallback (and shortfall to fallback/preferred where the template asks).
- For fees, escrow, indemnity caps/baskets: fill both the percent field and the derived dollar field.
- Months (survival, escrow release, TSA duration, non-compete): integers; compute delta-to-fallback months where asked.
- For exposure bands, take low/high from the workbench risk estimates and cite the stable estimate id; do not invent bands.
- Aggregate exposure: sum only the quantified components the template lists (some templates explicitly exclude components such as transition disruption — follow the template).

## 6. Closing blockers
- A consent or material-contract change-of-control provision is a **closing blocker** only if it is a required `closing_condition` (must be satisfied before closing). `notice_only` and `post_closing_covenant` items are not blockers — list them as non-blocking notices / tradeable issues where the template supports it.
- Regulatory clearances (e.g., HSR) that must occur before closing are blockers.
- Sum consent amount-at-risk and material-contract revenue conditioned from the blocker set.

## 7. Ordering and priority
- `priority_order` / `priority_rank`: highest negotiation priority to lowest, **unless the template states another rule** (e.g., "sort by issue_id ascending"). Read the ordering rule from the template and follow it.

## 8. Summary / aggregate metrics
- Counts (issue count, high/medium/low risk counts, missing-term count, blocker count) and dollar totals must be **derived from the issue/blocker set you built**, not invented. Recompute them whenever the set changes.

## Common analytical categories (non-exhaustive; the authoritative set is the task's template)
financing condition, reverse / break-termination fee, escrow / holdback, indemnity cap, indemnity basket, representation survival, materiality scrape, non-compete / non-solicit, employee continuity / PTO / service credit, transition services, tax allocation (Section 1060), transfer-tax split, governing law / forum, consent closing conditions, HSR / regulatory, material-contract conditions, D&O tail, working-capital adjustment.
