# M&A Deal Workbench — Reusable Operating Rules

## Purpose

This skill governs interaction with the M&A deal workbench — a structured API surface for reviewing acquisition agreements (APA, SPA, carveout, or other M&A transaction types). Apply these rules whenever the task involves the deal workbench, regardless of client side (buyer or seller), transaction structure, or deliverable format.

---

## Phase 1 — Environment Bootstrap

1. **Read `environment_access.md`** from the working directory. Extract:
   - `base_url` — the workbench root (e.g. `http://task-env:9020/`).
   - `credentials.read_only_sql_token` — the bearer token for `POST /api/query`.
   - `allowed_endpoints` — the full list of permitted routes. Do not call endpoints outside this list.

2. **Verify the base URL is reachable** by calling `GET <base_url>/` or `GET <base_url>/workspace`. If unreachable, surface the error; do not guess.

---

## Phase 2 — Task Parsing

From the task prompt, extract these immutables before any API call:

| Field | Source | Example |
|-------|--------|---------|
| `client_side` | "seller-side counsel" / "buyer-side counsel" | `seller` or `buyer` |
| `client_name` | Named entity the counsel represents | `Calyx Systems Inc.` |
| `counterparty_name` | The other side | `Northstar Holdings LLC` |
| `deal_id` | Project code in the prompt | `PRJ_JUNIPER` |
| `project_name` | Human-readable project name | `Project Juniper` |
| `target_name` | The company/asset being acquired | `Juniper Field Services` |
| `transaction_type` | APA, SPA, carveout, etc. | `asset purchase agreement` |
| `deliverable_type` | What to produce | `issue register`, `closing package`, `escalation memo`, `transition review`, `deviation matrix` |
| `answer_template_path` | Always `input/payloads/answer_template.json` | — |
| `playbook_id` | If stated (e.g. `PB_SELLER_A`, `PB_BUYER_A`) | `PB_SELLER_A` |
| `policy_id` | If the task references committee policies | — |

If the prompt does not state the playbook or policy ID explicitly, discover it: list playbooks via `GET /api/playbooks` or policies via `GET /api/policies`, then match to the client side and transaction type.

---

## Phase 3 — Load the Answer Template

1. **Read `input/payloads/answer_template.json`** in full.
2. Extract:
   - `allowed_enums` — every field with a restricted value set. Never emit a value outside these sets.
   - `required_top_level_fields` or `required_output_shape` — the exact structure the response must conform to.
   - `units` block — precision rules for currency, percentages, months.
   - `stable_*_ids` blocks — when the template pre-defines valid identifiers for issues, redlines, or categories, use only those identifiers.
3. Map each template field to the API endpoint(s) that will supply its data (see Phase 4).

---

## Phase 4 — Data Gathering

### 4a. Core Deal Record

```
GET <base_url>/api/deals/<deal_id>
```

Extract: headline purchase price, signing date, deal status, parties, transaction structure.

### 4b. Draft Terms

```
GET <base_url>/api/deals/<deal_id>/terms
```

Each term has a stable `term_id`. Capture: term text, clause reference, quantified values (percentages, dollar amounts, month durations). These are the **draft** positions to compare against the playbook.

### 4c. Applicable Playbook

```
GET <base_url>/api/playbooks/<playbook_id>/rules
```

Each rule encodes the client's **preferred** and **fallback** positions on a negotiable term. Map each draft term to its corresponding playbook rule by subject matter (indemnity cap, escrow, survival, non-compete, etc.). Where the draft is silent on a playbook-mandated term, classify it as `missing_required_term`.

### 4d. Policies (when committee/escalation tasks)

```
GET <base_url>/api/policies
GET <base_url>/api/policies/<policy_id>/thresholds
```

Policy thresholds define what requires committee escalation. Compare draft terms against policy thresholds; flag terms where the draft exceeds a threshold as `out_of_policy`.

### 4e. Risk Estimates

```
GET <base_url>/api/deals/<deal_id>/risk-estimates
```

Extract low/high exposure ranges per risk category. Use these to populate `quantified_exposure` / `total_modeled_exposure` fields.

### 4f. Supporting Records (gather all that exist for the deal)

| Endpoint | When needed |
|----------|-------------|
| `/api/deals/<deal_id>/employees` | Employee continuity, PTO liability, service credit, WARN risk |
| `/api/deals/<deal_id>/consents` | Closing consent conditions, counterparty risk |
| `/api/deals/<deal_id>/regulatory` | HSR, antitrust, hell-or-high-water, regulatory effort |
| `/api/deals/<deal_id>/benchmarks` | Market comparison for indemnity caps, baskets, survival periods |
| `/api/deals/<deal_id>/notes` | Negotiation history, open items, tradeable issues |
| `/api/deals/<deal_id>/cap-table` | Holder-level economics, fully-diluted percentages |
| `/api/deals/<deal_id>/material-contracts` | Contract consent conditions, annual revenue at risk |
| `/api/deals/<deal_id>/diligence-findings` | NWC adjustment basis, special indemnity, privacy findings |
| `/api/deals/<deal_id>/documents` | Reference documents, term sheets |

### 4g. Cross-Table SQL (when available)

```
POST <base_url>/api/query
Authorization: Bearer deal-workbench-readonly
Content-Type: application/json

{"query": "<SQL SELECT statement>"}
```

Use for cross-referencing records that span multiple endpoints — e.g. linking consent IDs to contract revenue, or verifying employee counts across tables. Never use `INSERT`, `UPDATE`, `DELETE`, or `DROP`.

---

## Phase 5 — Analysis & Comparison

### 5a. Playbook-to-Draft Comparison

For every term in the playbook:

1. **Find the corresponding draft term** by subject-matter matching (indemnity cap ↔ indemnity cap, not by term_id equality).
2. **Classify the gap:**
   - `in_policy` — draft falls within preferred-to-fallback range.
   - `out_of_policy` — draft violates a policy threshold.
   - `missing_required_term` — playbook requires the term; draft is silent.
   - `draft_exceeds_playbook` — draft is more aggressive than the playbook's preferred position.
   - `draft_below_playbook` — draft is weaker than the playbook's fallback position.
3. **Quantify the delta** between draft and playbook positions (percent points, dollar amounts, months) and between draft and fallback (`delta_to_fallback`).

### 5b. Issue Prioritization

Rank issues from highest to lowest negotiation priority. Heuristic:
1. Closing certainty issues (consents, regulatory, outside date).
2. Economics at risk (indemnity cap, escrow, basket, survival).
3. Employee and operational continuity.
4. Tax, governing law, and administrative terms.

### 5c. Risk Rating

- `HIGH` — exposes the client to unquantified liability, blocks closing, or cedes a fundamental protection.
- `MEDIUM` — economic exposure is bounded but material, or the issue is tradeable with concessions.
- `LOW` — cosmetic, administrative, or already within striking distance of resolution.

---

## Phase 6 — Quantification

### 6a. Dollar Amounts

- **Basis**: Calculate from the deal's headline purchase price unless a data source explicitly states a different basis (e.g. upfront cash, equity value).
- **Format**: Integer dollars (no cents, no decimals). Round to nearest integer.
- **Exposure ranges**: Populate `low` and `high` from risk-estimate records where available; otherwise compute from the draft-to-fallback gap.

### 6b. Percentages

- Match the template's precision directive: "two decimal places" means `12.50` not `12.5`; "one decimal place" means `12.5`.
- Unit is **percent points**, not basis points — a 2.5% indemnity cap is `2.50`, not `0.025`.

### 6c. Months

- Always integers. Round partial months per the template's directive (typically floor or round).

### 6d. Dates

- Use `YYYY-MM-DD` format.

### 6e. Holder Percentages

- When the template specifies "four decimals," use four decimal places (e.g. `0.1234` for 12.34%).

---

## Phase 7 — Output Assembly

1. **Build the JSON object** by populating every required field from the template with data gathered and computed in Phases 4–6.
2. **Omit optional fields** whose values are `null` only if the template explicitly allows `null`. When in doubt, include the key with a `null` value.
3. **Sort arrays** as directed by the template (by `issue_id`, by `redline_id`, by priority rank, etc.).
4. **Use stable identifiers** from the workbench for all `*_id` fields — never invent identifiers.
5. **Enum discipline**: Every string field with a constrained vocabulary must use exactly the values listed in `allowed_enums` or the template's inline enum comments.
6. **Language**: English only, unless the template specifies otherwise.
7. **No narrative outside JSON**: Return only the JSON object. No markdown fences, no explanatory prose, no commentary.

---

## Phase 8 — Validation (Before Returning)

1. Every `allowed_enums` field uses an allowed value.
2. Every `stable_*_id` field uses a value from the template's pre-defined list.
3. All dollar amounts are integers.
4. All percentages follow the template's precision directive.
5. Summary metrics are internally consistent (e.g. `issue_count` matches the length of `issue_register`; `high_risk_count` matches the count of HIGH-rated items).
6. Priority order array contains every issue_id from the issue register exactly once.
7. No invented identifiers, no prose outside JSON.

---

## Endpoint Quick Reference

```
# Discovery
GET  <base_url>/
GET  <base_url>/workspace

# Deal core
GET  <base_url>/api/deals
GET  <base_url>/api/deals/<deal_id>

# Deal sub-resources
GET  <base_url>/api/deals/<deal_id>/terms
GET  <base_url>/api/deals/<deal_id>/benchmarks
GET  <base_url>/api/deals/<deal_id>/risk-estimates
GET  <base_url>/api/deals/<deal_id>/cap-table
GET  <base_url>/api/deals/<deal_id>/consents
GET  <base_url>/api/deals/<deal_id>/employees
GET  <base_url>/api/deals/<deal_id>/material-contracts
GET  <base_url>/api/deals/<deal_id>/regulatory
GET  <base_url>/api/deals/<deal_id>/diligence-findings
GET  <base_url>/api/deals/<deal_id>/notes
GET  <base_url>/api/deals/<deal_id>/documents

# Playbooks & policies
GET  <base_url>/api/playbooks
GET  <base_url>/api/playbooks/<playbook_id>/rules
GET  <base_url>/api/policies
GET  <base_url>/api/policies/<policy_id>/thresholds

# Search & query
GET  <base_url>/api/search
POST <base_url>/api/query   # Bearer: deal-workbench-readonly
```

## Enum Reference

These sets appear across templates; use the exact value from the task's template — this is a consolidation, not an override.

**risk_rating**: `LOW`, `MEDIUM`, `HIGH`

**recommended_action**: `delete`, `revise`, `add`, `accept`, `escalate`, `approve`, `approve_with_conditions`, `reject`

**issue_status**: `in_policy`, `out_of_policy`, `missing_required_term`, `draft_exceeds_playbook`, `draft_below_playbook`

**Common business_outcome values**: `closing_certainty`, `escrow_economics`, `indemnity_exposure`, `restrictive_covenants`, `employee_transition`, `tax_allocation`, `governing_law`, `regulatory_efforts`
