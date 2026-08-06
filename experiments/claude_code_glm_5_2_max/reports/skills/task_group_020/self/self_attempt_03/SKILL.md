---
name: ma-deal-workbench-review
description: Produce a structured JSON legal-review deliverable for an M&A deal from the deal workbench API — an issue register, closing/economics package, committee escalation memo, carveout transition review, or SPA deviation matrix. Covers comparing the current draft terms against a seller/buyer playbook or a committee policy, classifying issues, quantifying dollar exposure from the correct value base, aggregating risk totals, and conforming exactly to a provided answer_template.json. Triggers on deal workbench, M&A issue register, SPA/APA deviation matrix, committee escalation memo, carveout transition review, playbook vs draft, policy thresholds, indemnity/escrow/survival analysis, closing blockers.
---

# M&A Deal Workbench Structured Review

Use this skill when a task asks you to act as buyer- or seller-side counsel on an M&A deal, gather deal records from the deal workbench, compare the current draft terms against a playbook or committee policy, and return **only** a JSON object that conforms to a provided `answer_template.json`.

The five recurring deliverable shapes this skill covers:

- **Issue register** — list of issues vs a playbook, with priority order and summary metrics.
- **Closing/economics package** — holder-level consideration allocation, indemnity/escrow/survival/NWC, consents, regulatory, covenants, D&O tail/expenses, closing readiness.
- **Committee escalation memo** — only the draft terms that are out-of-policy or restricted for committee approval (distractors excluded).
- **Carveout transition review** — IP/domain transition, TSA scope/fees, §1060 allocation, transfer-tax split, employee continuity, outside-date protection, governing law/forum.
- **SPA deviation matrix** — buyer positions on indemnity/survival/scrape/escrow/consents/HSR/material contracts, plus closing blockers and risk totals.

The method is the same for all five. Only the standard (playbook vs policy), the sub-resources needed, and the output schema change — and the answer template tells you the last two.

## Prerequisites

- `environment_access.md` is staged in the working directory. It is the **only** source for network access: it gives the workbench base URL, the `POST /api/query` token, and the allowlist of endpoints. Do not use any other network source.
- A task prompt naming a `deal_id`, a side (buyer/seller), and a deliverable shape.
- An `answer_template.json` defining the exact output contract.

## Procedure

### 1. Read `environment_access.md` first
Capture the base URL, the `/api/query` token, and the allowed-endpoint list. Use only endpoints on that list. If the base URL is given as `<TASK_ENV_BASE_URL>`, substitute the real value from `environment_access.md`.

### 2. Load `answer_template.json` before fetching anything
The template is the contract. Build a checklist from it:
- Required top-level fields and per-object fields.
- `allowed_enums` (risk_rating, recommended_action, issue_status, business_outcome, etc.) — every emitted enum value must match **exactly**, including case.
- `units` — the precision for currency, percent points, and months. **Precision varies by task** (whole percent, 1 dp, 2 dp, 4 dp for holder percentages); read it, do not assume.
- Any `stable_issue_ids` / `stable_redline_ids` / `possible_issue_ids` — use these verbatim as IDs; do not invent new ones.
- Ordering rules for arrays (by issue_id ascending, by priority, etc.).
- The summary-metrics / risk-totals / aggregate-summary block — these are the exact metrics to compute; do not invent extras.

### 3. Fetch the deal record
`GET /api/deals/<deal_id>` returns the `deal` object plus a `links` map to every sub-resource. From the deal object capture:
- `client_side` (buyer/seller), `transaction_type` (APA / SPA / merger / carveout) — these set the analysis posture.
- The **value basis** fields used to quantify dollars: `headline_value`, `upfront_cash`, `stock_value`, `milestone_value`.
- The **governing standard**: `playbook_id` and/or `policy_id` (one or both may be null).

### 4. Identify and fetch the governing standard (scoped)
- **Negotiation-position reviews** (issue register, transition review, deviation matrix, closing package) → use the **playbook** named in the prompt/deal record: `GET /api/playbooks/<playbook_id>/rules`. Each rule carries `preferred_position`, `fallback_position`, `limit_value`, `limit_unit`, `basis`, `required_action`, `risk_default`.
- **Committee escalation** → use the **policy**: `GET /api/policies/<policy_id>/thresholds`. Each threshold carries `threshold_value`, `threshold_unit`, `restricted_flag`, `approval_required`, `policy_standard`, `basis`.

Always use the **path-scoped** endpoint (with the id in the URL). If you use `POST /api/query` for cross-table checks instead, you **must** filter `playbook_rules`/`policy_thresholds` by the deal's specific `playbook_id`/`policy_id`. Those tables hold rows for *all* playbooks/policies; an unscoped join produces cross-standard contamination (e.g., one category appearing with two conflicting thresholds from different policies).

### 5. Gather the sub-resources the task needs
Pull them from the `links` map (equivalently `/api/deals/<deal_id>/<resource>`). Typical set: `terms`, `consents`, `employees`, `regulatory`, `benchmarks`, `risk-estimates`, `diligence-findings`, `notes`, `material-contracts`. Add `cap-table` for SPA holder allocation; `documents` for version tracking. Key fields per resource are in `references/workbench_api.md`. Do not fetch resources the deliverable does not use.

### 6. Filter distractors before comparing
The workbench intentionally contains noise. Clean it first:
- Drop draft terms where `staleness_flag != "current"`.
- De-duplicate categories that repeat from an earlier draft.
- Match on the **exact `deal_id`**; ignore similarly-named projects (e.g., two projects whose names differ by one letter are different deals with different terms).
- For committee tasks specifically: escalate **only** `restricted_flag="yes"` terms that breach their threshold. Exclude in-policy terms, non-restricted terms, and terms whose `approval_required` is below committee level — these are deliberate distractors.
- When a term's source conflicts, prefer the latest document version.

### 7. Compare each current draft term to its matching standard by `category`
For each draft term, find the standard rule/threshold with the same `category` and classify `issue_status`:
- `in_policy` — draft is at or inside the preferred/standard position.
- `draft_exceeds_playbook` — draft is harsher than the fallback allows (higher cap/escrow, longer survival, larger fee than the side's fallback).
- `draft_below_playbook` — draft is weaker than preferred (or below a buyer-preferred minimum) but within fallback.
- `out_of_policy` — draft breaches a policy threshold (committee tasks).
- `missing_required_term` — no current draft term exists for a category the side's position requires. Use `source_term_ids: []`. Treat draft silence as an issue **when the standard demands an affirmative provision** and the surrounding deal data (consents, employees, regulatory, diligence) shows the term is needed.

Assign `risk_rating` (LOW/MEDIUM/HIGH) from the rule's `risk_default`, the term severity, and the quantified dollar exposure. Pick `recommended_action` from the template enum, guided by the rule's `required_action`. The full classification table is in `references/comparison_method.md`.

### 8. Quantify dollars from the correct base
Read each term's/rule's `basis` field; do not default to `headline_value`:
- `purchase price` / `equity value` → `headline_value`
- `upfront cash` → `upfront_cash`
- `enterprise value` → `headline_value` unless the deal record gives a distinct EV
- `identified findings` / a specific finding or consent → that record's `amount` / `amount_at_risk`

`amount = percent_points × base`, rounded to **integer USD**. If a source text states an explicit dollar amount on a different basis, use the stated amount. Compute `delta_to_fallback` (and `delta_to_preferred` / `shortfall_to_fallback` where the template asks). Quantification detail in `references/comparison_method.md`.

### 9. Position against benchmarks (when the template asks)
Use `/api/deals/<id>/benchmarks`: `median_value`, `upper_quartile`, `sample_size` set the benchmark `position` enum (at_or_below_median / between_median_and_upper_quartile / at_upper_quartile / above_upper_quartile / not_applicable).

### 10. Aggregate summary metrics
Compute exactly the metrics the template's summary block lists (e.g., issue_count, high_risk_count, total_quantified_exposure_low/high, total_negotiation_delta, required_closing_consent_count, total_employee_count, total_pto_liability, closing_blocker_count). For exposure totals, sum the `risk_estimates` categories the task says to **include** and exclude the ones it says to **exclude** (e.g., a task may include closing-certainty + indemnity but exclude transition-disruption). Do not invent metrics.

### 11. Emit only JSON
Return a single JSON object conforming to the template. No prose, no markdown fences, no commentary. Every enum value spelled exactly as in `allowed_enums`. Nulls only where the template permits null. Stable IDs copied verbatim from the workbench (term_id, consent_id, contract_id, finding_id, employee_id, holder name). Arrays sorted per the template's ordering instructions.

## Pitfalls (confirmed against the workbench)

- **Unscoped SQL joins contaminate.** `playbook_rules` and `policy_thresholds` hold all standards. A join without `WHERE playbook_id=<deal's>` / `policy_id=<deal's>` returns conflicting thresholds for the same category. Prefer the path-scoped REST endpoints; if you must use SQL, filter by the deal's standard id.
- **Stale/duplicate rows.** Always filter `staleness_flag="current"`. Committee deals carry stale in-policy rows as distractors.
- **Wrong value base.** "equity value" usually means `headline_value`, not `stock_value`. Read `basis`.
- **Percent precision varies.** Whole / 1 dp / 2 dp / 4 dp — read the template's `units`.
- **Committee distractors.** In-policy and non-restricted terms must be excluded, not escalated.
- **Missing-term issues.** Need `source_term_ids: []` and `issue_status: missing_required_term` — do not skip a required category just because the draft is silent.
- **"Return only JSON" is literal.** Any prose outside the object fails the task.

## References

- `references/workbench_api.md` — full endpoint catalog, auth, and the 14-table data model with key fields per resource.
- `references/comparison_method.md` — issue-status classification table, quantification basis map, benchmark positioning, and aggregation rules.
- `references/formatting.md` — per-type units/precision, enum conformance, stable-ID and ordering rules, and JSON-only output discipline.
