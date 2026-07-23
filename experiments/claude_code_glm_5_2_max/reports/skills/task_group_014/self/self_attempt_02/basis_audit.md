# basis_audit Construction

Every Northstar answer template requires a `basis_audit` object with four keys. It is the
audit trail that explains *why* the answer is what it is, in terms of environment record IDs.

```
"basis_audit": {
  "source_precedence":       "<one of the six rules>",
  "precedence_record_order": ["id", "id", ...],
  "controlling_record_ids":  ["id", "id", ...],
  "exception_record_ids":    ["id", "id", ...]
}
```

## source_precedence

Select from the six-rule taxonomy in `decision_rules.md` based on the task archetype (or the
controlling factor for cross-cutting tasks). One value, exactly.

## controlling_record_ids

The environment record IDs whose values **directly determine the answer** — the records you
actually relied on to compute the recommendation/status/amount/route.

- Ordering: **operational evidence order** — the order in which the records operationally
  drive the result (typically: the primary target record first, then the evidence/criteria
  records that set the result, then the authorization/decision record).
- Examples by archetype (substitute real IDs; do not copy these literal placeholders):
  - UM prior-auth: the case, the current clinical + POC documents and their facts, the
    authorization record.
  - Appeal: the appeal record, the documented drug trial(s), the met criteria evidence.
  - Repricing: the claim, the chosen current benchmark rows, the claim lines.
  - P2P: the P2P event, the case_criteria results, the authorization record.
  - Margin queue: the queue rows (`month_id`s) that set the actions.

## exception_record_ids

The record IDs that **explain an exclusion, denial, missing information, or route priority**
— the gaps and rejected/exception records.

- Ordering: **business gap/exception order** — criteria or route gaps **before** stale or
  excluded records when both appear. Concretely: (1) unmet/unclear criteria and route-priority
  gaps, (2) missing-information records (undocumented trials, assistance missing fields,
  missing factors), (3) stale/excluded/rejected records (stale exports, rejected stale
  benchmarks, distractor schedules).
- Examples by archetype:
  - UM prior-auth: the stale-export document (excluded); any `gap_description`-bearing
    criterion when the case pends.
  - Appeal: the undocumented drug trial (evidence gap), the assistance `missing_fields`
    (assistance gap).
  - Repricing: the rejected stale-source benchmark row; any non-matching distractor schedule
    rows you explicitly rejected.
  - P2P: the missing-factor fact(s) / unresolved criteria; the denial-bearing authorization.
  - Margin queue: the below-threshold row(s) (shortfall gap) and the charge-sensitive flag
    rows.

## precedence_record_order

The merged, prioritized list of **both** controlling and exception record IDs, ordered by
the `source_precedence` rule, **highest priority first**. This is the single ordered trail a
reviewer can follow.

- Build it by concatenating `controlling_record_ids` and `exception_record_ids` and then
  sorting according to what the precedence rule says is most important:
  - `current_clinical_records_over_stale_export` → current clinical records first, stale
    exports last.
  - `payer_appeal_before_manufacturer_assistance` → payer-appeal records (appeal + evidence +
    criteria) before assistance records; within appeal, controlling before gap.
  - `effective_benchmark_by_plan_modifier_and_date` → the effective current benchmark and its
    claim lines first; the rejected stale source and distractors last.
  - `new_patient_specific_p2p_information` → the P2P event and new-information criterion
    first; missing factors / unresolved criteria / denial record after.
  - `margin_threshold_then_charge_sensitivity` → below-threshold (margin-driving) rows first,
    then charge-sensitivity rows.
  - `appeal_deadline_then_clinical_then_payment_integrity` → deadline-bearing record first,
    then clinical records, then payment-integrity records.
- Every ID in `controlling_record_ids` or `exception_record_ids` should appear in
  `precedence_record_order`; an ID should not be duplicated.

## Practical notes

- Use the **environment's own IDs** verbatim (`case_id`, `appeal_id`, `p2p_id`, `auth_id`,
  `document_id`, `fact_id`, `trial_id`, `benchmark_id`, `claim_line_id`, `month_id`,
  criterion IDs, source names where the template treats a source as a record). When a
  "record" is a benchmark *source* rather than a single row, use the `benchmark_id`(s) or the
  `source_name` per the template's item type (string).
- Keep lists ordered exactly as the template's `ordering_rule` states; when a template gives
  an explicit ordering rule, it overrides a default sort.
- If a category is genuinely empty (no exceptions, e.g. a clean approval), emit an empty
  list `[]` — do not omit the key.
