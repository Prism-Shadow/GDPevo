---
name: ma-deal-workbench-review
description: Use when acting as M&A transaction counsel (seller- or buyer-side) reviewing a deal draft against a seller/buyer playbook or an M&A Committee policy, gathering deal data from the M&A deal workbench over the network, and returning a structured JSON deliverable (issue register, deviation matrix, committee escalation memo, buyer economics/closing package, or carveout transition review) that conforms to a provided answer_template.json. Read this before producing the JSON.
---

# M&A Deal Workbench Review

## When this skill applies

A task asks you to act as M&A transaction counsel for a specific deal and produce a
**structured JSON** deliverable. Recognition signals in the prompt:

- A named **deal_id** (e.g. `PRJ_…`) and a stated **client_side** (`seller` or `buyer`).
- A workbench base URL placeholder such as `<TASK_ENV_BASE_URL>`.
- A reference to an **answer template** at `input/payloads/answer_template.json`.
- A request to review draft terms against a **playbook** (`PB_SELLER_*` / `PB_BUYER_*`)
  or a **committee policy** (`POL_MA_*`), and to quantify exposure, classify issues,
  order by priority, and summarize.
- The deliverable types this skill covers: seller APA issue register, buyer SPA
  economics/closing package, M&A Committee escalation memo, carveout transition review,
  buyer SPA deviation matrix.

If the prompt matches the above, follow this skill end to end.

## The three inputs — read all before working

1. **The prompt** — your role, `client_side`, `deal_id`, what the deliverable must cover,
   and any precision/units rules stated inline.
2. **`environment_access.md`** — the **only** sanctioned way to reach the running
   environment. It contains a `GDPEVO_ENV_BASE_URL=…` line and a read-only SQL token
   (on the `POST /api/query` line). Parse it fresh every run; do not hardcode the URL
   or token in your output or scripts.
3. **`input/payloads/answer_template.json`** — the exact output contract for *this* task.
   Each task's template differs: it defines the top-level fields, per-issue fields,
   allowed enums, stable issue/redline IDs, units, and ordering rules. Your JSON must
   conform to **this** template, not a generic one.

## Resolve access

- Parse `environment_access.md` → `base_url` (strip trailing slash) and `sql_token`.
- The workbench is a read-only HTTP service. All `GET` endpoints return JSON; the full
  list, payload shapes, and field names are in `references/workbench_api.md`.
- Read-only SQL: `POST {base_url}/api/query` with JSON body
  `{"token": sql_token, "sql": "<SELECT …>"}` → `{"columns": […], "row_count": N, "rows": [[…]]}`.
  Use it for cross-table checks (e.g. join `draft_terms` to `playbook_rules`). Fourteen
  backing tables mirror the REST resources.
- `scripts/fetch_deal.py` reads `environment_access.md` for you and pulls every
  sub-resource for a `deal_id` plus the governing playbook/policy into one JSON blob.

## Workflow (detail in `references/analysis_workflow.md`)

1. **Load the deal record** — `GET /api/deals/<deal_id>` → `client_side`, `playbook_id`,
   `policy_id` (may be null), `headline_value`, `currency`, signing/meeting dates.
2. **Pull every linked sub-resource** for that `deal_id` (terms, consents, employees,
   material-contracts, diligence-findings, risk-estimates, benchmarks, regulatory,
   cap-table, notes, documents). Use the `links` map on the deal record.
3. **Pull the governing positions** — `GET /api/playbooks/<playbook_id>/rules`; if
   `policy_id` is set, also `GET /api/policies/<policy_id>/thresholds`.
4. **Map each template issue / stable ID** to its draft term(s) and compare against the
   playbook preferred/fallback or the policy threshold. Classify status, quantify against
   the purchase price, assign risk_rating, recommended_action, business_outcome, and the
   required position.
5. **Treat draft silence as an issue** — when the client position requires an affirmative
   provision and the draft is silent, record `missing_required_term` with empty
   `source_term_ids`. Conversely, **exclude** terms the prompt says to drop (stale,
   in-policy, or non-committee distractors) — check `staleness_flag` and policy
   `restricted_flag` / `approval_required`.
6. **Build the summary layer** — priority order (highest negotiation priority → lowest),
   and the template's summary metrics / aggregate summary / risk totals / closing
   readiness, recomputed from the issues you kept.
7. **Emit only valid JSON** conforming to the template; validate enums, stable IDs,
   units, and ordering before returning.

## Classification & units (detail in `references/classification_and_units.md`)

- **`issue_status` semantics flip with client_side.** Seller reviewing a buyer draft: a
  buyer-favorable term beyond the seller playbook = `draft_exceeds_playbook`; a seller
  protection that is absent or too weak (e.g. no reverse break fee) = `draft_below_playbook`
  or `missing_required_term`. Buyer reviewing a seller draft: a cap below the buyer fallback
  = `draft_below_playbook`; a cap above what the buyer wants may still be `draft_below_playbook`
  relative to the buyer's *preferred* position — classify against the side's playbook, not
  the counterparty's.
- **Quantify from `headline_value`** unless a source explicitly states a different basis.
  Currency = integer USD. Percent points at the precision the prompt/template states
  (two decimals, one decimal, or whole — they differ by task). Months = integers.
  Dates = `YYYY-MM-DD`.
- **Reuse stable IDs from the template** for issues/redlines; cite workbench source IDs
  verbatim (`term_id`, `consent_id`, `contract_id`, `employee_id`, `finding_id`,
  `estimate_id`, `benchmark_id`, `document_id`).

## Output discipline

- Return **only** JSON. No explanatory prose, no markdown fences, no commentary outside
  the object/array.
- Conform to the **specific** `answer_template.json` for this task — field names, enums,
  and stable IDs vary across deliverable types.
- Sort arrays per the template's ordering instructions (by `issue_id` ascending, by
  `priority_rank`, by counsel-workflow priority, etc.).
- **Do not assume** records from a similarly-named project apply to your `deal_id`;
  always filter resources by the exact `deal_id`.
- If a field is not applicable to an issue, use the template's null/`not_applicable`
  convention rather than inventing a value.

## Reference files

- `references/workbench_api.md` — every endpoint, auth, payload field shapes, SQL usage.
- `references/analysis_workflow.md` — step-by-step review, quantification, priority, summaries.
- `references/classification_and_units.md` — enum vocabulary, status semantics by side, units/rounding, stable-ID conventions.
- `scripts/fetch_deal.py` — fetch all sub-resources + playbook/policy for a `deal_id`, reading access from `environment_access.md`.
