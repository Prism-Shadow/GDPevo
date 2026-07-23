# Classification & Quantification Patterns

Side-specific status direction, common issue sets by deal type, and quantification rules. Transferable patterns — no deal-specific values.

## Status direction depends on client side

The same draft value can be `draft_exceeds_playbook` for one side and `draft_below_playbook` for the other. Direction is always from **your client's** perspective: "exceeds" = the draft gives the counterparty more than your framework allows; "below" = the draft gives your client less protection than your framework requires.

### Seller-side (framework = seller playbook)
Seller-protective terms cap the buyer's recourse and limit post-closing exposure. A draft that is **more buyer-favorable than the seller's ceiling** is `draft_exceeds_playbook`:
- indemnity cap **above** the fallback % (e.g. draft 18% vs fallback 12.5%)
- survival **longer** than the fallback months
- escrow **larger %** or **longer release** than the fallback
- a buyer **financing condition** present (seller prefers none)
- transition services **longer** than the fallback, or fees that **exclude** stranded cost (below-cost support)

A draft that is **less seller-protective than the floor** is `draft_below_playbook`:
- reverse break-up fee of **0%** when the fallback requires a fee
- no materiality scrape when the seller position would accept one (rare; usually a buyer ask)

`missing_required_term` for seller: transition services (carveout), IP/domain transition, Section 1060 allocation, transfer-tax split, outside-date extension, governing-law/forum, employee continuity/PTO allocation, HSR covenant — when absent and the deal data shows need.

### Buyer-side (framework = buyer playbook)
Buyer-protective terms maximize recourse and walk rights. A draft that is **less buyer-protective than the floor** is `draft_below_playbook`:
- indemnity cap **below** the fallback % (e.g. draft 8% vs fallback 10%)
- survival **shorter** than preferred, or at fallback without the required escrow
- **no** materiality scrape, or breach-only when full is preferred
- consents **excluding** material contracts (e.g. payer gateways)
- employee service credit **disclaimed**

A draft that is **more seller-favorable than the buyer allows** is `draft_exceeds_playbook` (e.g. MAE carveouts beyond the approved list/count). `missing_required_term` for buyer: escrow/holdback (when survival fallback requires one), HSR clearance condition, material-contract consent conditions.

For buyer packages, a single field named `*_required` (e.g. `materiality_scrape_required`) typically expects the buyer's **preferred** position, not the fallback.

## Risk rating
Default to the framework rule's `risk_default` (playbook) capitalized to the template's enum (`LOW`/`MEDIUM`/`HIGH`). For policy/committee items, rate by severity of the breach. Acceptable-fallback matches can stay at the rule's default or step down one level; do not invent ratings not supported by the framework or the data.

## Recommended action
- `add` — term is missing (`missing_required_term`).
- `revise` — term exists but deviates (`draft_exceeds_playbook` / `draft_below_playbook` / `out_of_policy`).
- `delete` — strike an unwanted provision (e.g. seller removing a buyer financing condition).
- `accept` — draft sits at an acceptable fallback (`in_policy`).
- `escalate` — the framework's `required_action` says "Escalate …" and the deviation matches, or the risk is high.
- `approve_with_conditions` / `approve` / `reject` — committee/policy recommendation fields.

## Quantification rules

### Base selection
- Default base = deal `headline_value`.
- If a term or framework rule states `basis: enterprise value` or `basis: equity value`, use the headline value as that base (for these workbench deals the headline value is the enterprise/equity value). The term's own prose often confirms the dollar result (e.g. "equal to X million dollars") — use it to validate your base.
- Special-indemnity and finding amounts are absolute dollars from the term/finding, not %-derived.

### Per-term dollars
For a percent-of-base term with draft `d%`, preferred `p%`, fallback `f%`:
- `draft_amount = d% × base`, `preferred_amount = p% × base`, `fallback_amount = f% × base`
- if draft exceeds fallback: `delta_to_fallback = draft_amount − fallback_amount`
- if draft below fallback/preferred: `shortfall_to_fallback = fallback_amount − draft_amount`, `shortfall_to_preferred = preferred_amount − draft_amount`

For month terms: report `draft_months`, `preferred_months`, `fallback_months`, and the month delta (no dollar conversion unless the template asks).

### Aggregates
- **Aggregate quantified exposure**: sum `exposure_low` and `exposure_high` over the risk-estimate categories the template includes. Watch the template's `included_exposure_components` / `excluded_exposure_components` lists — they tell you which categories to sum and which to drop.
- **Negotiation delta**: sum of per-term dollar deltas/shortfalls to fallback across the quantified terms.
- **Closing consent amount at risk**: `sum(amount_at_risk)` over consents with `required_for_closing: yes`.
- **Material-contract revenue requiring consent**: `sum(annual_revenue)` over material contracts with `consent_required: yes`.
- **Employee totals**: `sum(count)` and `sum(pto_liability)` across employee groups.
- **Headline value**: the deal's `headline_value`, integer.

### Holder allocation (SPA/closing packages)
- `total_consideration = fully_diluted_pct × headline_value` per holder, using the **stored** `fully_diluted_pct`.
- `cash_amount = fully_diluted_pct × upfront_cash`, `stock_amount = fully_diluted_pct × stock_value` (same pro-rata blend for every holder).
- Sums across holders must reconcile to `upfront_cash`, `stock_value`, and `headline_value`.

## Common issue sets by deal type

### Carveout / divestiture APA (seller-side transition review)
Expect issues for: transition services scope/duration/fees (vs. seller playbook ≤ preferred months, fallback months if fees cover stranded cost); stranded-cost reimbursement gap (excluded overhead dollars); customer-consent termination rights; field-employee continuity & PTO; IP/domain transition; Section 1060 allocation; transfer-tax split; outside-date extension; governing-law/forum. Quantified exposures typically include stranded-cost gap, field-ops PTO liability, required-closing-consent amount at risk, top-customer annual revenue at risk, and transition-disruption high estimate.

### Stock purchase agreement — buyer closing/economics package
Cover: economics & holder-level allocation; indemnity (cap/survival/scrape) package; escrow/holdback (basis, %, amount, release months/trigger, status); NWC adjustment (collar from working-capital finding); required closing consents and material-contract conditions; non-blocking notices; employment (service-credit IDs, PTO, WARN-risk IDs); restrictive covenants for rollover holders; D&O tail and transaction-expense allocation; regulatory (HSR, hell-or-high-water, closing condition); closing readiness (status, risk, blocker IDs, tradeable issue IDs, consent amount at risk, material-contract revenue conditioned, PTO total).

### Public-company merger — committee escalation memo
Escalate only current draft terms that are out-of-policy or committee-restricted; exclude stale/in-policy/non-committee terms. Per escalated term: draft metric, policy metric (threshold + required triggers/approved groups), delta (points, amount, months, removed triggers, excess count), benchmark support (median/UQ/position; `not_applicable` where no benchmark exists), exposure (type/low/high/source estimate id), recommendation, required conditions. Aggregate: escalated count, excluded terms/categories, risk counts, aggregate quantified exposure (only included components), RTF excess amount, overall recommendation, committee action, negotiation priority.

### Buyer SPA deviation matrix
One row per position (indemnity cap & basket; survival & knowledge qualifier; materiality scrape; escrow/holdback & release; consent closing condition; HSR condition; material contracts). Each row carries status, risk, recommended action, a specific `final_position` (the template enumerates these 1:1 with the issues), priority rank, the relevant percent/month/contract-count/amount fields, shortfalls to fallback and preferred, special-indemnity and privacy-finding amounts, and `*_status` flags (`not_found_in_current_records` / `found` / `not_applicable`) for basket, knowledge qualifier, escrow agent, and release. Close with closing blockers (consent / regulatory / material-contract types) and risk totals (counts by status and risk, consent amount at risk, material-contract revenue requiring consent, cap shortfalls, total modeled exposure low/high, highest-exposure category).

### Seller APA issue register
Issue set = draft terms deviating from the seller playbook + absent seller-protective terms the data shows are needed. Each issue carries business outcome, status, risk, action, required position code, the percent/month/amount triple with delta, and any relevant booleans/codes (service credit, field selection, hell-or-high-water, HSR, regulatory effort, tax allocation, governing law/forum). Summary metrics: issue count, risk counts, business-outcome count, headline value, aggregate exposure low/high, total negotiation delta, required closing consent count, employee count, PTO total.
