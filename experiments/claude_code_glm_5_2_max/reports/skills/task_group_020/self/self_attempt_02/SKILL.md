---
name: ma-deal-workbench-review
description: Produce a structured JSON deliverable for an M&A deal workbench task — issue register, deviation/position matrix, transition review, committee escalation, or closing/economics package. Use when a task assigns you as buyer-side or seller-side counsel for a named deal (deal_id like PRJ_*), points at a workbench via <TASK_ENV_BASE_URL>, and requires a single JSON object conforming to an answer_template.json.
---

# M&A Deal Workbench Review

Reusable operating rules distilled from the train tasks. These rules apply to **any** workbench task that names a deal, points at `<TASK_ENV_BASE_URL>`, and asks for JSON conforming to an `answer_template.json`. They contain no task-specific final values — fill every value from the live workbench at runtime.

## When to use
Trigger this skill when the task:
- assigns a side (buyer-side / seller-side / committee counsel) and a `deal_id` (the `PRJ_*` pattern);
- references a deal workbench at `<TASK_ENV_BASE_URL>` and lists API entry points;
- asks for a structured JSON deliverable conforming to `input/payloads/answer_template.json`, with no narrative outside the JSON.

## 0. Resolve workbench access (network config comes from ONE place)
- Read `environment_access.md` in the working directory. It is the **only** source for:
  - the base URL — the `GDPEVO_ENV_BASE_URL` value that `<TASK_ENV_BASE_URL>` in the prompt maps to;
  - the read-only SQL token for `POST /api/query`;
  - the allow-list of endpoints.
- Do not hardcode the base URL or token, and do not invent endpoints outside the allow-list. Re-read this file each run.

## 1. Parse the engagement
- **Side** → buyer-side vs seller-side. This selects the playbook (`PB_BUYER_A` / `PB_SELLER_A` pattern — use the exact playbook_id named in the prompt) and the protective direction every term is judged against.
- **deal_id** → take it verbatim from the prompt. Never substitute a similarly-named project's records.
- **Transaction type** → APA, SPA, or carveout APA (drives which mechanics apply: cap-table/holder allocation for SPA, Section 1060 + transfer-tax + TSA for carveout, etc.).
- **Deliverable shape** → read `answer_template.json` first; it defines every required field, enum, and stable ID list. The template is the contract.

## 2. Gather the deal record
Pull the records the prompt lists **and** the records the template's fields imply. Minimum set (see `references/workbench_endpoints.md` for what each returns):
- deal record + terms, side-appropriate playbook rules, policy thresholds (if committee/escalation);
- risk-estimates, employees, consents, material-contracts, regulatory, diligence-findings, benchmarks, cap-table, notes, documents — as the template requires.
- Use `POST /api/query` (token from `environment_access.md`) **only** for cross-table joins; it is read-only and secondary to the GET endpoints.

## 3. Compare draft against the correct playbook / policy
- Map each current draft term to its matching playbook rule or policy threshold.
- Classify with the template's `issue_status` enums: `in_policy`, `out_of_policy`, `missing_required_term`, `draft_exceeds_playbook`, `draft_below_playbook`.
- **Draft silence is an issue** when your side's position requires an affirmative provision — record it as `missing_required_term` (e.g., seller needs an escrow release trigger; buyer needs an HSR clearance condition; carveout needs a Section 1060 allocation).
- **Exclude distractors** per the task's scope: drop stale, in-policy, or out-of-scope terms unless the task explicitly asks for them (e.g., a committee escalation lists only out-of-policy / restricted terms).

## 4. Quantify from the correct base
- Compute dollar amounts from the deal's **headline purchase price** unless a source explicitly states a different basis (upfront cash, identified findings, etc.).
- For each issue derive draft vs. preferred vs. fallback amounts/months/percent and the **delta to fallback**.
- Use the workbench's risk estimates for exposure low/high ranges and cite the source `estimate_id`.

## 5. Formatting discipline (follow the precision the prompt/template states)
- Currency → integer USD dollars.
- Percent points → decimal to the precision stated in that task's prompt/template (commonly two decimals; sometimes one decimal or whole points; holder/security percentages may require four decimals).
- Months → integers. Dates → `YYYY-MM-DD`.
- **Stable source IDs only** — reuse `term_id`, `consent_id`, `contract_id`, `finding_id`, `employee_id`, holder names, and `estimate_id` exactly as the workbench returns them. Never invent IDs.
- Every enum and every stable ID must come from the answer template's `allowed_enums` / `possible_issue_ids` / `stable_*_ids` lists.

## 6. Assemble the deliverable
- Build one JSON object matching `answer_template.json` exactly: top-level fields, nested objects, and array-element shapes.
- Sort as instructed: issues by `issue_id` ascending or by counsel workflow; provide `priority_order` from highest to lowest negotiation priority.
- Include the aggregate/summary block the template requires: issue and risk counts, quantified exposure low/high, negotiation deltas, consent/employee/PTO totals, closing-blocker counts, final-position / overall-posture / closing-readiness classification.

## 7. Output
- Return **only** the JSON object — no prose, no markdown fences, no commentary.
- Validate it parses and conforms to the template before finishing.

## References
- `references/workbench_endpoints.md` — endpoint catalog and the fields each returns.
- `references/output_cheatsheet.md` — per-field type/precision and enum quick reference.
