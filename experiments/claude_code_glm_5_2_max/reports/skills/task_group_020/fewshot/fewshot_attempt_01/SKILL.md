---
name: ma-deal-workbench-review
description: Produces a structured JSON deliverable for an M&A deal-review task driven by the running deal workbench — asset/stock purchase agreement issue registers, SPA closing & economics packages, carveout transition reviews, M&A committee escalations, and SPA deviation matrices. Use when a task casts you as buyer-side or seller-side counsel, points you at a deal workbench reachable over the network, asks you to compare draft terms against a playbook or committee policy, classify issues by status/risk, quantify dollar exposure from the purchase price, and return only JSON conforming to a shipped answer_template.json. Reads base URL and read-only SQL token from environment_access.md and never imports another deal's schema, IDs, or values.
---

# M&A Deal Workbench Review

Produce a structured JSON deliverable for an M&A deal-review task by querying the running deal workbench, comparing the current draft against the applicable playbook or committee policy, and emitting JSON that conforms to the task's own `answer_template.json`.

## Read these first, in order
1. **The task prompt** — gives the `deal_id`, `client_side` (buyer/seller), deliverable type and required coverage, the playbook/policy id to compare against, and the unit/precision rules.
2. **`input/payloads/answer_template.json`** — the authoritative schema for THIS task: required fields, allowed enums, stable ID lists, ordering rules, and units. Templates differ across tasks; do not carry another task's schema forward.
3. **`environment_access.md`** — use it **only** to reach the running environment over the network (base URL, read-only SQL token, allowed-endpoint list). It is not a source of deal data or answer values.

## Workflow
1. **Extract task parameters** from the prompt (deal_id, client_side, deliverable, playbook/policy id, precision rules).
2. **Reach the workbench** — read `environment_access.md`; substitute its base URL for every `<TASK_ENV_BASE_URL>` in the prompt. See `references/workbench_access.md`.
3. **Pull records by exact deal_id** — deal record, draft terms, playbook rules (and/or policy thresholds), risk estimates, employees, consents, material contracts, regulatory, benchmarks, diligence findings, cap table, documents, notes. Pull what the deliverable needs. Do **not** assume records from a similarly named project apply.
4. **Classify each relevant term** against the playbook/policy — `issue_status`, `risk_rating`, `recommended_action` (and `redline_action` where the template has redlines). Derive allowed enum values from THIS task's template. See `references/analysis_method.md`.
5. **Handle missing terms and distractors** — treat a missing/silent required term as an issue when the client's position needs an affirmative provision; exclude stale/in-policy/distractor terms only when the task says to.
6. **Quantify from the purchase-price base** — dollars from the headline purchase price unless a source states a different basis; quantify the draft against the playbook's preferred and fallback positions; compute deltas/shortfalls; take exposure bands from risk estimates.
7. **Build ordering, blockers, and summary metrics** — priority order per the template's rule; closing blockers are required closing conditions + regulatory clearances only; derive all counts/totals from the set you built.
8. **Emit JSON** conforming to THIS task's template, with the task's units/precision, using stable workbench IDs. See `references/output_contract.md`.

## Critical rules
- **Conform to THIS task's `answer_template.json`** — its fields, enums, stable IDs, ordering, and units. Never import a prior deal's schema.
- **Use stable IDs from the workbench**; never invent or reuse IDs from another deal. `source_term_ids` is `[]` for a missing required term.
- **Quantify from the deal's headline purchase price** unless a source explicitly states a different basis.
- **Units/precision vary per task** — read them from the prompt + template and follow exactly.
- **Return only valid JSON**; no narrative outside it.
- **Query by the exact `deal_id`**; do not let a similarly named project's records bleed in.

## References
- `references/workbench_access.md` — reaching the workbench: base URL, token, endpoint catalog, read-only SQL.
- `references/analysis_method.md` — classification, quantification, missing-term/distractor handling, blockers, ordering, summary metrics.
- `references/output_contract.md` — template conformance, per-task units/precision, stable IDs, JSON-only, no cross-deal values.
