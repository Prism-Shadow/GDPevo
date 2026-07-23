---
name: ma-deal-workbench-review
description: Produce a structured-JSON M&A legal-review deliverable (issue register, closing/economics package, committee escalation memo, carveout transition review, or deviation matrix) from the running M&A deal workbench, strictly conforming to a provided answer_template.json. Use when acting as buyer- or seller-side counsel on a PRJ_* deal/project and told to return only JSON.
---

# M&A Deal Workbench Review

## When to use this skill

Use this skill when a task asks you to act as **buyer- or seller-side transaction counsel** for a specific M&A deal/project and produce a **structured JSON** deliverable by querying the running **M&A deal workbench**. Recognize the family by these signals:

- A deal/project ID such as `PRJ_…`, a named client and target/counterparty, and a side (buyer or seller).
- An instruction to use the workbench at `<TASK_ENV_BASE_URL>` (web UI + REST APIs), often with a read-only SQL endpoint and a token.
- An `answer_template.json` (under `input/payloads/`) that defines the exact output schema, plus an instruction like "return only JSON" / "do not include narrative outside the JSON".

If the task does not point to the deal workbench or does not provide an answer template, do not use this skill.

The deliverable type varies (issue register, closing/economics package, committee escalation memo, carveout transition review, SPA deviation matrix). The shape is always dictated by **the answer_template.json in front of you** — see `references/deliverable_patterns.md` for the recurring patterns.

## The contract: the answer_template.json is the source of truth

Before writing anything, open `input/payloads/answer_template.json` and read it end to end. It defines:

- the required top-level fields and their nesting,
- the **exact field names** (spell them exactly — no synonyms, no extra fields),
- the **allowed enum values** (issue_status, risk_rating, recommended_action, business_outcome, blocker_type, final_position, etc.),
- the **units and precision** (integer USD; percent points as decimals at a template-specified precision — 1 dp, 2 dp, or whole; integer months; `YYYY-MM-DD` dates; holder percentages to four decimals),
- the **stable-ID vocabularies** (e.g. `possible_issue_ids`, `stable_issue_ids`, `stable_redline_ids`) — use only IDs from these lists or from the workbench,
- the **required ordering** (sort by issue_id ascending, by priority rank, by redline_id, etc.).

Never invent fields, enum values, or IDs. If the template enumerates allowed values, use only those. Templates vary across tasks in precision and field set — always follow **the template in front of you**, never a remembered default.

## Environment access

Reach the workbench **exactly as documented in `environment_access.md`** — that file is the only authorized network path. It gives the base URL, the allowed GET endpoints, and the read-only SQL token. Do not invent endpoints or tokens. See `references/workbench_reference.md` for endpoint families and the real response shapes.

## Procedure

### 1. Orient
From the prompt, extract: client side (buyer/seller), client name, deal_id (`PRJ_…`), target/counterparty, the deliverable type, and the answer-template path. Note any explicit scope instructions (e.g. "exclude stale/in-policy distractors", "do not assume records from similarly named projects apply to this deal", "calculate from the correct purchase-price base").

### 2. Pull the deal record and the comparison reference
- `GET /api/deals/<deal_id>` → the deal record carries `client_side`, `headline_value`, `upfront_cash`, `stock_value`, `milestone_value`, `currency`, `playbook_id`, `policy_id`, `signing_date`, `meeting_date`, `transaction_type`, plus a `links` map to every sub-resource.
- Side + `playbook_id`/`policy_id` decide the comparison reference:
  - buyer side → a buyer playbook (`PB_BUYER_*`) and/or a committee policy (`POL_*`),
  - seller side → a seller playbook (`PB_SELLER_*`).
- `GET /api/playbooks/<playbook_id>/rules` for the preferred + fallback position per category.
- `GET /api/policies/<policy_id>/thresholds` for committee thresholds (note `restricted_flag` and `approval_required`).

### 3. Gather the deal's sub-resources
For the deal_id, pull every sub-resource the template's fields imply: `terms` (the draft terms under review), `consents`, `employees`, `material-contracts`, `benchmarks`, `risk-estimates`, `regulatory`, `cap-table`, `diligence-findings`, `notes`, `documents` (see `references/workbench_reference.md` for shapes). Use `POST /api/query` (read-only SQL) for cross-table joins and counts (e.g. count consents required for closing, sum PTO liability by employee group, join draft_terms to playbook_rules on category).

### 4. Review and classify (see `references/review_methodology.md`)
For each draft term — **and for each protective term the playbook/policy requires that is absent from the draft**:

- Map the term to a playbook rule / policy threshold by `category` (and `basis`).
- Classify `issue_status`:
  - draft silent/absent on a required term → `missing_required_term`, `source_term_ids: []`, action `add`;
  - draft present but worse than the fallback → `draft_exceeds_playbook` (seller view of buyer-friendly drift) or `draft_below_playbook` (buyer view of seller-friendly drift), action `revise`;
  - draft at or better than the preferred position → `in_policy`, action `accept`;
  - draft crosses a policy threshold or is restricted → `out_of_policy`, action `escalate`/`approve_with_conditions`/`reject` per the policy.
- Assign `risk_rating` (LOW/MEDIUM/HIGH) — start from the rule's `risk_default`, then adjust using deal-specific risk-estimates and exposure magnitude.
- Choose `recommended_action` from the allowed enum.
- Capture the affirmative position the skill asks for (`required_position_code`, `final_position`, `must_have_terms`, or `required_position_normalized`).
- **Exclude distractors**: stale terms (`staleness_flag` set), in-policy terms, and terms outside the requested scope — unless the template explicitly asks for them.

### 5. Quantify (see `references/review_methodology.md`)
- Dollar amounts are **integer USD**, computed from the deal's `headline_value` (or the basis a source states — e.g. equity value, `upfront_cash`) × the relevant percent. When a source states an explicit basis, use it; otherwise default to the headline purchase price.
- Percent fields: decimals at the template's precision. Months: integers. Dates: `YYYY-MM-DD`.
- Compute the negotiation gap: `delta_to_fallback_*` = the gap between the draft and the fallback position; `shortfall_*` = required − draft where the draft falls short of a required minimum.
- Pull exposure low/high from `risk-estimates` by matching `category`; cite the `estimate_id`.
- Pull benchmark median/upper_quartile/sample_size from `benchmarks`; classify the draft's position versus the quartiles.

### 6. Prioritize and aggregate
- Build `priority_order` / `priority_rank` / `negotiation_priority`: highest negotiation priority first, driven by `risk_rating` and closing-certainty / indemnity impact.
- Build the summary/aggregate block so **every count reconciles** with the issue list (`issue_count` = length of register, `high_risk_count` = count of HIGH, `out_of_policy_issue_count`, `missing_required_term_count`, `closing_blocker_count`, etc.). Sum quantified exposure from the **included** components only; if the template has fields for excluded components (e.g. `transition_disruption`), list them explicitly.

### 7. Emit and self-check
- Output **only** a single JSON object conforming to the template. No prose, no markdown fences, no commentary outside the JSON.
- Before finishing, self-check:
  - every required field is present and spelled exactly as in the template;
  - every enum value is one of the template's allowed values;
  - every array is sorted per the template's ordering instructions;
  - stable IDs are copied verbatim from the workbench (never invented or paraphrased);
  - all counts and totals reconcile with the line items;
  - units and precision match the template;
  - the JSON parses.

## References
- `references/workbench_reference.md` — endpoint families, response shapes, and the read-only SQL interface.
- `references/review_methodology.md` — classification, quantification, prioritization, and aggregation/reconciliation rules.
- `references/deliverable_patterns.md` — the recurring deliverable shapes and what each section must capture.
