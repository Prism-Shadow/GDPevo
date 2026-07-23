# Analysis Workflow

Step-by-step method for producing the deliverable. Run it top to bottom. Every numbered
step maps to a section of the output template.

## 0. Read the contract first

Before fetching anything, read `input/payloads/answer_template.json` and note:
- the **top-level shape** (e.g. issue register + priority_order + summary_metrics;
  or position_matrix + closing_blockers + risk_totals; or memo + escalation_terms +
  aggregate_summary);
- the **stable IDs** you must reuse for issues/redlines and the **enums** you must use
  verbatim;
- the **ordering** instructions (by `issue_id` ascending, by `priority_rank`, by counsel
  priority, etc.);
- the **units/precision** the template or prompt demands.

The template is the spec; the workbench is the evidence.

## 1. Load the deal record

`GET /api/deals/<deal_id>` → capture `client_side`, `playbook_id`, `policy_id`,
`headline_value`, `currency`, `signing_date`, `meeting_date`, `client_name`,
`project_name`, `target_name`, `counterparty_name`. These populate the memo header and
the percentage base.

Confirm the `deal_id` exists in `GET /api/deals` if anything is ambiguous — do not let a
similarly-named project's records bleed in.

## 2. Pull all sub-resources

Follow the `links` map and fetch every sub-resource for the `deal_id`. You will typically
need: `terms`, `consents`, `employees`, `material-contracts`, `diligence-findings`,
`risk-estimates`, `benchmarks`, `regulatory`, `cap-table`, `notes`, `documents`. Not
every deliverable uses every resource, but gather them once and select what the template
asks for. (`scripts/fetch_deal.py` does this in one pass.)

## 3. Pull the governing positions

- `GET /api/playbooks/<playbook_id>/rules` — the preferred and fallback positions, with
  `limit_value` / `limit_unit` and a `risk_default`.
- If `policy_id` is set (escalation-memo tasks), `GET /api/policies/<policy_id>/thresholds`
  — the committee thresholds, `restricted_flag`, and `approval_required`.

Match a draft term to a playbook rule or policy threshold by `category`.

## 4. Build the issue / position list

For each stable issue ID (or category) the template defines:

1. **Find the draft term(s).** Match by `category` (and `clause_ref` where useful). If no
   draft term exists and the client position requires an affirmative provision, this is a
   `missing_required_term` issue with `source_term_ids: []`.
2. **Compare to the playbook/policy position.** Read `preferred_position` /
   `fallback_position` (or `threshold_value`). Determine whether the draft exceeds, falls
   below, matches, or omits the position.
3. **Classify** `issue_status` (see `classification_and_units.md` — semantics depend on
   `client_side`).
4. **Quantify.** Convert the draft and preferred/fallback percentages to dollars using
   `headline_value` (or the source's stated `basis`). Compute the delta to fallback (and
   to preferred, where the template has both). Months come straight from the term/rule.
5. **Assign** `risk_rating`, `recommended_action`, `business_outcome` (where the template
   has it), and a `required_position_code` / `required_position_normalized` /
   `must_have_terms` object describing the seller's or buyer's required fix.
6. **Cite sources.** Put the workbench `term_id`/`consent_id`/`contract_id`/
   `employee_id`/`finding_id`/`estimate_id`/`benchmark_id` into `source_term_ids` /
   `source_record_ids` verbatim.

## 5. Exclude distractors

Drop terms the prompt says to exclude. Common exclusion rules observed across tasks:
- **Stale terms** — `staleness_flag: true` on a draft term (unless the task wants them).
- **In-policy terms** — draft already at or within the playbook/policy position; for
  escalation memos, exclude categories where `restricted_flag`/`approval_required` is false
  or the term is within threshold.
- **Non-committee categories** — for M&A Committee memos, only escalate categories the
  policy marks restricted / approval-required.

Record what you excluded only if the template has an `excluded_*` field; otherwise just
omit.

## 6. Quantify exposure and deltas

- For each issue with a dollar dimension, compute `draft_amount`, `preferred_amount`,
  `fallback_amount`, and `delta_to_fallback` (draft − fallback, signed the way the
  template expects — usually the absolute gap the client must close).
- For break-fee / shortfall issues, compute `required_fee_*` and `shortfall_*` against the
  fallback.
- Pull low/high exposure from `risk_estimates` by matching `category`; tag with
  `source_estimate_id`. If no estimate exists, use `not_quantified` / null per template.
- Summarize into the template's exposure fields: low/high totals, negotiation delta total,
  consent amount at risk, material-contract revenue conditioned, employee/PTO totals.

## 7. Build priority order

Produce the `priority_order` / `priority_rank` / `negotiation_priority` the template asks
for. Priority is a **counsel-workflow** judgment, not alphabetical: rank by
closing-certainty and dollar exposure first (financing condition, reverse break fee,
escrow, indemnity cap), then employee/transition and restrictive covenants, then
survival/basket, then tax and governing law. Tie-break by `risk_rating` (HIGH > MEDIUM >
LOW) then by dollar delta. The exact order is deal-specific; the *method* is stable.

## 8. Build the summary layer

Recompute every summary field from the issues you **kept** (not from the raw data):
- counts: issue_count, high/medium risk counts, missing_required_term count,
  draft_below/above_playbook counts, out_of_policy count;
- dollar totals: headline value, quantified exposure low/high, negotiation delta,
  required-consent amount at risk, material-contract revenue conditioned, PTO total;
- readiness: overall_status (READY / READY_WITH_CONDITIONS / NOT_READY), blocker IDs,
  tradeable issue IDs, overall recommendation / committee_action.

Do not carry forward a number from a sub-resource without re-deriving it through the kept
issue set — distractor exclusion changes the totals.

## 9. Validate and emit

- Every enum value is in the template's `allowed_enums` / inline enum list.
- Every issue/redline ID is from the template's stable-ID list.
- Units match: integer USD, percent points at the stated precision, integer months,
  `YYYY-MM-DD` dates.
- Arrays sorted per the template's ordering instructions.
- Output is **only** the JSON object/array — no prose, no fences.
