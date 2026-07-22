# M&A Deal Workbench Review Skill

## Overview

This skill provides a reusable workflow for reviewing M&A transaction records using a deal workbench REST API. It covers seller-side and buyer-side deal review, committee escalation, carveout transition review, and deviation matrices across asset purchases, stock purchases, and mergers.

## Environment

The deal workbench is a running REST API. Its base URL is provided as `<TASK_ENV_BASE_URL>` in task prompts (typically `http://task-env:9020/`). A read-only SQL endpoint is available at `POST /api/query` with bearer token `deal-workbench-readonly`. All GET endpoints are unauthenticated.

### Available API Endpoints

**Deal-level records:**
- `GET /api/deals/<deal_id>` — deal metadata, headline purchase price, parties, structure
- `GET /api/deals/<deal_id>/terms` — current draft agreement terms
- `GET /api/deals/<deal_id>/documents` — agreement documents and exhibits
- `GET /api/deals/<deal_id>/benchmarks` — market benchmark data for terms
- `GET /api/deals/<deal_id>/risk-estimates` — quantified risk estimates
- `GET /api/deals/<deal_id>/cap-table` — capitalization table (stock deals)
- `GET /api/deals/<deal_id>/consents` — third-party consent requirements
- `GET /api/deals/<deal_id>/employees` — employee data, counts, PTO liability
- `GET /api/deals/<deal_id>/material-contracts` — material customer/supplier contracts
- `GET /api/deals/<deal_id>/regulatory` — HSR, antitrust, and other regulatory facts
- `GET /api/deals/<deal_id>/diligence-findings` — diligence findings and flags
- `GET /api/deals/<deal_id>/notes` — deal team and negotiation notes

**Reference data:**
- `GET /api/playbooks` — list available playbooks
- `GET /api/playbooks/<playbook_id>/rules` — playbook rules (preferred and fallback positions)
- `GET /api/policies` — list available policies
- `GET /api/policies/<policy_id>/thresholds` — policy thresholds for committee approval
- `GET /api/search` — search across records (use sparingly)

**Cross-table queries:**
- `POST /api/query` — read-only SQL. Send `{"token": "deal-workbench-readonly", "query": "<SQL>"}`. Use for cross-table checks when a single endpoint is insufficient.

### Web UI fallback

The workbench also has a web UI at the base URL. You may browse `/workspace` to navigate deal records visually if the API alone is insufficient, but prefer the API for structured data extraction.

## General Workflow

### Phase 1 — Gather Records

1. **Identify the deal, your client side (buyer/seller), and the applicable playbook or policy** from the task prompt.
2. **Fetch the deal record** (`GET /api/deals/<deal_id>`) to extract:
   - Headline purchase price (the basis for all dollar calculations)
   - Deal structure (asset purchase, stock purchase, merger)
   - Counterparty names and key dates
3. **Fetch draft terms** (`GET /api/deals/<deal_id>/terms`) — these are the current draft agreement provisions.
4. **Fetch the playbook or policy rules** — the source of truth for your client's positions:
   - For playbook-driven reviews: `GET /api/playbooks/<playbook_id>/rules`
   - For policy/committee reviews: `GET /api/policies/<policy_id>/thresholds`
5. **Fetch all supporting records** relevant to the task scope. At minimum:
   - Risk estimates (`/risk-estimates`)
   - Consents (`/consents`) — identify closing conditions and amounts at risk
   - Regulatory (`/regulatory`) — HSR status, thresholds, hell-or-high-water
   - For stock deals: cap table (`/cap-table`)
   - For employment issues: employees (`/employees`) — counts, PTO liability, service credit needs
   - For material contracts: material-contracts (`/material-contracts`) — revenue at risk
   - For diligence-backed issues: diligence-findings (`/diligence-findings`)
   - For benchmark comparisons: benchmarks (`/benchmarks`)
   - For deal-team context: notes (`/notes`) and documents (`/documents`)

### Phase 2 — Compare Draft vs. Playbook/Policy

For each relevant term category, compare the **draft value** against the **playbook preferred** and **playbook fallback** (or **policy threshold**) values:

1. **Draft exceeds playbook** — the draft is worse for your client than the fallback. Flag as an issue with `recommended_action: "revise"`.
2. **Draft below playbook** — the draft is better than the fallback but below preferred. If the delta is material, flag with `recommended_action: "revise"` or `"add"` to seek improvement.
3. **Missing required term** — no draft term exists but the playbook/policy requires an affirmative provision. Flag with `recommended_action: "add"`.
4. **In policy** — the draft is within acceptable bounds. Mark accordingly; exclude from escalations unless the task asks for full registers.

**Critical rule**: Treat absent seller-protective or buyer-protective terms as issues when the surrounding deal data shows the term is needed (e.g., HSR is required but no HSR condition exists in the draft).

### Phase 3 — Calculate Quantified Impacts

All dollar calculations flow from the headline purchase price unless a specific record (risk estimate, consent record, employee data) states a different basis.

**Standard calculation rules:**
- **Currency**: Integer dollars (no cents). Round to nearest integer.
- **Percentages**: Follow the answer template's precision. Common conventions:
  - Percent points to two decimal places for policy comparisons
  - Percent points to one decimal place for economics summaries
  - Whole percent points for transition reviews
  - Holder percentages to four decimals for cap-table allocations
- **Months**: Integer values.
- **Dates**: `YYYY-MM-DD` format.
- **Dollar amounts from percent**: `headline_value × (percent / 100)`, rounded to integer.
- **Delta amounts**: `draft_amount - fallback_amount` or `fallback_amount - draft_amount` depending on whether the draft is above or below the desired position. The delta should represent how much the draft deviates from the fallback.

**Stable IDs**: Always use the exact IDs from the workbench records (term IDs, consent IDs, contract IDs, risk estimate IDs, employee IDs). Never invent IDs. Use empty arrays `[]` for source fields when a term is missing from the draft.

### Phase 4 — Prioritize and Summarize

**Priority ordering** — rank issues from highest negotiation priority to lowest. General heuristics:
- Closing certainty issues (financing conditions, reverse break fees, HSR, regulatory) typically rank highest.
- Economics (escrow, indemnity caps) come next.
- Employee/operational continuity follows.
- Governance (governing law, tax allocation) typically rank lower.
- Within a tier, prefer higher risk rating and larger quantified exposure.

**Summary metrics** — aggregate across all issues:
- Count issues by risk rating (HIGH, MEDIUM, LOW)
- Sum quantified exposures (low and high estimates)
- Count required closing consents, employees, PTO liability
- Compute total negotiation delta across all issues

### Phase 5 — Produce the Answer

1. **Read the answer template** from `input/payloads/answer_template.json`. It defines the exact JSON shape, allowed enums, and required fields.
2. **Fill every required field** per the template. Use `null` only where the template explicitly allows it and the value is genuinely unavailable.
3. **Use allowed enums exactly** as spelled in the template. Do not invent new enum values.
4. **Return only JSON** — no explanatory prose, no markdown fences unless the task explicitly permits them. The response must be parseable as a single JSON object.
5. **Sort arrays** as the template instructs (typically by stable ID or by priority rank).

## Task-Type Specific Guidance

### Seller-Side APA Issue Register (buyer-drafted paper)
- Compare buyer draft against seller playbook rules.
- Issue categories typically include: financing conditions, reverse break fees, escrow (percent, amount, release months), indemnity cap and basket, survival periods, non-compete/non-solicit, employee continuity, transition services, tax allocation, governing law/forum, consent conditions, materiality scrape, HSR covenants.
- For each issue provide: source term IDs, business outcome, issue status, risk rating, recommended action, required position code, and all applicable draft/playbook/delta values.
- Dollar amounts derived from headline purchase price.

### Buyer-Side SPA Closing & Economics Package
- Cover economics (headline value, upfront cash, stock, milestones), holder-level allocation from cap table, indemnity package (cap, survival, materiality scrape), escrow (basis, amount, release), NWC adjustment.
- Identify closing conditions: required consents, material-contract conditions, non-blocking notices.
- Cover employment covenants (service credit, PTO, WARN risk), restrictive covenants, D&O tail and transaction expenses.
- Assess regulatory: HSR required, threshold basis, hell-or-high-water.
- Produce closing readiness assessment: overall status, risk rating, blockers vs. tradeable issues.

### M&A Committee Escalation Package
- Read the committee policy thresholds first — they define what needs escalation.
- Only escalate terms that are **out of policy**. Exclude in-policy terms (list them in the excluded section).
- For each escalated term: provide draft metric, policy metric, delta, benchmark comparison (median, upper quartile, position), quantified exposure (low/high), recommendation, and required conditions.
- Categories typically include: reverse termination fee, fiduciary out, rep & warranty survival, MAE carveouts.
- Aggregate summary includes risk counts, total quantified exposure, excess RTF amount, overall recommendation, committee action text, and negotiation priority.

### Carveout APA Transition Review
- Focus on transition and separation terms specific to carveout deals.
- Key categories: IP/domain transition (trademark license, domain redirect), TSA scope/duration/fees, Section 1060 purchase-price allocation, transfer-tax split, employee continuity (field/operations), customer consent conditions, closing deadline/outside date extensions, governing law/forum.
- For each transition issue: normalize draft values and required positions into comparable shapes.
- Provide required redlines linked to issues, each with redline action and must-have terms.
- Summarize operational risk: overall posture, quantified exposures (stranded costs, PTO, consent amounts at risk, revenue at risk, disruption estimates), required closing consent IDs, business outcomes protected.

### SPA Deviation Matrix (Buyer-Side)
- Compare each position category against buyer playbook.
- For each issue: source term IDs, status, risk rating, recommended action, final position (from template enum), priority rank.
- Track: draft vs. preferred vs. fallback percents, months, amounts, shortfalls.
- Special fields: basket status, knowledge qualifier status, escrow agent status, release status (found/not_found/not_applicable).
- Identify closing blockers: consent blockers, regulatory blockers, material-contract blockers — each with blocker type, risk rating, amounts at risk, annual revenue, required action.
- Risk totals aggregate: headline purchase price, issue counts by status, closing blocker count, consent amount at risk, contract revenue requiring consent, indemnity cap shortfalls, modeled exposure range, highest exposure category.

## Common Pitfalls to Avoid

1. **Wrong purchase-price basis**: Always use the headline purchase price from the deal record for percent-to-dollar conversions unless a specific record states otherwise.
2. **Inventing IDs**: Never fabricate term, consent, contract, employee, or risk-estimate IDs. Pull them directly from workbench records.
3. **Silent omissions**: If the task asks for all issues of a certain type, produce them all — don't skip low-risk or in-policy items unless the template explicitly says to exclude them.
4. **Enum mismatches**: Match allowed enum values exactly as spelled in the answer template. Case and underscores matter.
5. **Unit errors**: Confirm the template's required precision for percentages. Some ask for two decimal places, some for one, some for whole points.
6. **Extra-text contamination**: Return only the JSON object. No markdown fences, no preamble, no "Here is the answer" — unless the task prompt explicitly allows narrative.
7. **Cross-deal contamination**: Do not assume records from one deal apply to another. Each deal has its own isolated data.
8. **Overlooking missing terms**: A term missing from the draft is itself an issue when the playbook/policy/transaction facts require it. Flag it with empty `source_term_ids` and status `missing_required_term`.
