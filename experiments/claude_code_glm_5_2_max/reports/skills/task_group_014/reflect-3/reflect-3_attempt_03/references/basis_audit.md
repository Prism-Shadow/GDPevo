# basis_audit Construction

Every Northstar determination ends with a `basis_audit` object:

```json
"basis_audit": {
  "source_precedence": "<one of the six rules>",
  "precedence_record_order": ["..."],
  "controlling_record_ids": ["..."],
  "exception_record_ids": ["..."]
}
```

It is the same shape across all task types. The four fields interact:

- **`source_precedence`** — the single rule that decides which records win.
  Pick by task type (see SKILL.md table). This choice is the anchor; get it
  right first.
- **`controlling_record_ids`** — the environment record IDs that **directly
  control the result**, in operational evidence order (the order a reviewer
  processes them: evidence first, then the primary output record).
- **`exception_record_ids`** — the record IDs that **explain a gap, exclusion,
  denial, missing information, or route priority**. Order: criteria/route gaps
  first, then stale/excluded records (when both kinds appear).
- **`precedence_record_order`** — the union of controlling + exception records,
  listed in source-precedence order, **highest priority first**. In practice:
  controlling records first (in their operational order), then exception
  records (in gap order).

## What counts as a "record ID"

Use the environment's primary-key/business identifier for each record you cite:
`document_id`, `fact_id`, `auth_id`, `appeal_id`, `claim_id`, `claim_line_id`,
`trial_id`, `p2p_id`, `benchmark_id`, `month_id` (margin row). Cite records by
their stable IDs, not by criterion keys or free text.

## controlling_record_ids — pattern

Include the records that establish the determination. Consistently this is:

1. the **current, valid evidence records** that satisfy the met criteria
   (current clinical documents, the appeal packet documents, the documented
   drug trial, the cardiology note, etc.), then
2. the **primary output record** of the task type:
   - UM authorization → the `authorizations` record (auth_id);
   - pharmacy appeal → the `appeals` record (appeal_id);
   - claim repricing → the `claims` record, the remittance/EOB document, the
     claim lines, and the **current** benchmark records;
   - P2P summary → the `p2p_events` record and the `authorizations` record;
   - margin queue → all the in-scope `service_margin` queue rows.

Do **not** put a rejected/stale/gap record in `controlling_record_ids` — that
goes in `exception_record_ids`.

## exception_record_ids — pattern

Include the record(s) that explain why the result is what it is when there is a
gap, exclusion, denial, or route priority. One per task, typically:

- UM authorization with a stale export → the stale/non-current document
  (`is_current = 0`).
- Pharmacy appeal with a partial failure evidence set → the **undocumented**
  drug trial (`documented = 0`).
- Claim repricing paid on a stale schedule → the **rejected/stale** benchmark
  record (the older source whose effective window predates the service date).
- P2P summary where a superiority factor is absent → the document **fact**
  whose value is "not documented" (the `fact_id` tied to the not-met criterion).
- Margin queue with a below-threshold segment → the below-threshold
  `service_margin` row (it drives the priority route and the gap-to-threshold).

If a task genuinely has no gap/exclusion/route-priority record, the list can be
empty — but every Northstar task in this family has had one, so look carefully
before leaving it empty.

## precedence_record_order — pattern

Concatenate controlling then exception, keeping the controlling records in their
operational evidence order and appending the exception record(s) in gap order.
The "highest priority first" ordering follows the source-precedence rule:

- `current_clinical_records_over_stale_export` → current evidence first, stale
  last.
- `payer_appeal_before_manufacturer_assistance` → payer-appeal records first,
  assistance/gap records after.
- `effective_benchmark_by_plan_modifier_and_date` → current benchmark (matched
  by plan/modifier/date) first, rejected stale source last.
- `new_patient_specific_p2p_information` → the P2P event (source of the
  new-information decision) first, then clinical evidence, then the gap fact.
- `margin_threshold_then_charge_sensitivity` → below-threshold (threshold-gap)
  row first, then charge-sensitive rows.

## Worked shapes (record types, not values)

- **UM auth (approve, stale export excluded):**
  controlling = [current eval doc, current plan-of-care doc, authorization];
  exception = [stale export doc].
- **Pharmacy appeal (partial failures):**
  controlling = [member-auth doc, denial doc, prescriber-letter doc,
  documented drug trial, appeal]; exception = [undocumented drug trial].
- **Claim repricing (stale schedule):**
  controlling = [claim, remittance doc, claim line(s), current benchmark(s)];
  exception = [stale benchmark].
- **P2P summary (superiority factor absent, upheld):**
  controlling = [p2p event, clinical note, authorization];
  exception = ["not documented" fact for the not-met criterion].
- **Margin queue (one below-threshold segment):**
  controlling = [all in-scope queue rows]; exception = [the below-threshold
  queue row].

## Common mistakes to avoid

- Putting the rejected/stale record in `controlling_record_ids` instead of
  `exception_record_ids`.
- Omitting the primary output record (auth/appeal/claim/p2p) from
  `controlling_record_ids`.
- Forgetting that `precedence_record_order` is the **union** of both lists,
  not just the controlling list.
- Using a criterion key or free text instead of a stable environment record ID.
- Reordering lists against the template's stated ordering rule
  (operational/gap order, not alphabetical, for these audit lists — unless the
  template says otherwise).
