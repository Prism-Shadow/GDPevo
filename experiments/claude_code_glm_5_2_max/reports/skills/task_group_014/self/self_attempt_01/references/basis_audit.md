# basis_audit Reference

Every Northstar answer template requires a `basis_audit` object with exactly four keys. It is the audit trail of *why* the answer is what it is, and it is scored independently of the rest of the answer.

```json
"basis_audit": {
  "source_precedence": "<one rule from the enum>",
  "precedence_record_order": ["<id>", "..."],
  "controlling_record_ids": ["<id>", "..."],
  "exception_record_ids": ["<id>", "..."]
}
```

## source_precedence — pick the ONE rule that controls this task

| Rule | When it applies | What it means |
|---|---|---|
| `current_clinical_records_over_stale_export` | UM authorization tasks | Current clinical records / current plan of care (`documents.is_current=1`) control the determination; stale exports (`is_current=0`) never override them. |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeal + assistance tasks | The payer appeal path and packet are resolved first; the manufacturer assistance screen is secondary and conditional on the appeal. |
| `effective_benchmark_by_plan_modifier_and_date` | Claim repricing tasks | The benchmark is chosen by matching plan/modifier and the service date falling inside the benchmark's effective window; stale sources are rejected. |
| `new_patient_specific_p2p_information` | Peer-to-peer summary tasks | New patient-specific information from the P2P event can materially change (overturn) the intended review. |
| `margin_threshold_then_charge_sensitivity` | Margin queue tasks | Below-threshold payer-service segments are the primary issue; charge-sensitive rows are a secondary, separately-monitored category. |
| `appeal_deadline_then_clinical_then_payment_integrity` | Tasks where a deadline calculation drives routing | Deadline first, then clinical status, then payment-integrity considerations. |

Pick the single rule whose logic actually drove the result. If two seem to apply, choose the one that controls the *primary* decision (e.g. a P2P task with an adverse result still uses `new_patient_specific_p2p_information`, not the deadline rule — the deadline is a downstream consequence).

## controlling_record_ids

Environment record IDs that **directly control the result** — the records without which the answer would differ.

Order: **operational evidence order** — the order in which the records were applied to reach the decision, roughly:

1. The target case / appeal / claim / queue record itself.
2. The controlling policy and the criteria definitions that gate the decision.
3. The per-case criterion results that resolved the gate.
4. The evidence records (current documents / facts / benchmark rows / margin rows) that satisfied or failed those criteria.
5. The decision record (authorization, appeal outcome, P2P outcome) that the result enacts.

Include IDs at the granularity the environment exposes: `case_id`, `policy_id`, `criterion_id`, `document_id`, `fact_id`, `benchmark_id`, `month_id`, `appeal_id`, `p2p_id`, `auth_id`, `claim_line_id` — whichever records are load-bearing for this specific answer.

## exception_record_ids

Records that explain a gap, exclusion, denial, missing information, or route priority — i.e. why the answer is *not* something else.

Order: **business gap order** — criteria/route gaps first, then stale or excluded records when both appear:

1. Criteria or route gaps (e.g. a `criterion_id` whose `result` is `not_met`/`unclear` with a `gap_description`; a missing packet item; an unresolved PET factor).
2. Stale or excluded records (e.g. `document_id` with `is_current=0`; a `benchmark_id` whose source is stale; an excluded document).

## precedence_record_order

The **union** of `controlling_record_ids` and `exception_record_ids`, listed in **source-precedence order, highest priority first**. This is the single ordered trail a reviewer would follow: the most authoritative controlling record first, then down through the rest, with exception/gap records placed where they explain a deviation.

Concretely: lead with the controlling records in operational order, then interleave exception records by the precedence rule (e.g. for `current_clinical_records_over_stale_export`, current clinical records and the criteria they satisfy come before the stale export that was rejected).

## Worked shape (illustrative, not a real answer)

For a UM auth where the current eval + current plan of care satisfy all criteria and a stale export was excluded:
```
source_precedence: current_clinical_records_over_stale_export
controlling_record_ids: [CASE-..., POL-..., <criterion_ids in eval order>, DOC-...(current), DOC-...(current POC), AUTH-...]
exception_record_ids: [DOC-...(stale_export)]
precedence_record_order: [CASE-..., POL-..., <criteria>, DOC-...(current eval), DOC-...(current POC), AUTH-..., DOC-...(stale_export)]
```
Re-derive every ID from the current task's environment — never reuse IDs from another task.
