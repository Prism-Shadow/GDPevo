# Correction tasks (controlled write + audit)

Some requests ask you to apply a **minimal canonical correction** rather than
only report. These involve `/api/sql/transaction` and `/api/correction-audit`
in addition to read queries. The request payload supplies an
`approved_correction` block (reason code, actor, audit id, correction key,
corrected-at timestamp) and a `correction_status_rule` with `APPLIED` /
`NOT_APPLIED` conditions. The answer template usually forbids arrays and asks
for a correction target, mutation result, audit record, before/after backlog
analysis, and the final status enum.

## Rules that must not be broken

- **Change exactly one canonical field on exactly one business row.** Scope is
  "minimal canonical field only".
- **Never modify** raw/source values, source-identity fields, or any unrelated
  business row.
- Write **one** audit row for the change, using the values from the request's
  `approved_correction` (audit id, correction key, reason code, actor,
  corrected-at) plus the discovered entity/source ids and old/new values.
- Report `APPLIED` **only if** the request's success rule is actually met
  (typically: exactly one business row and one audit row committed **and** a
  post-change read confirms the new canonical value). Otherwise report
  `NOT_APPLIED` with the counts/values you actually observed — do not fabricate
  success.

## Procedure

1. **Locate the contradiction read-only.** Query `/api/sql` to find the single
   row where the raw source value and the canonical/effective value disagree in
   the way the request describes (e.g. a carrier scan whose canonical status
   contradicts its raw status). Capture the stable ids (scan/source row id,
   shipment/entity id), the field name, and the current `old_value` and the
   intended `new_value`.
2. **Measure the pre-correction metric** (e.g. backlog shipment count at the
   cutoff) with a read query, so you can report the before value and the delta.
3. **Apply the correction** via `/api/sql/transaction`. Build the request body
   from the shape documented in `/api/data-dictionary` (the empty/guessed body
   is rejected with `invalid request`; do not assume its structure — read the
   dictionary). The transaction must update the single canonical field and
   insert the single audit row, atomically. Use
   `python3 skill/scripts/atlas_api.py tx body.json`.
4. **Verify post-change** with fresh read queries:
   - the corrected row now shows the new canonical value;
   - exactly one business row and one audit row changed;
   - re-check `/api/correction-audit` (params come from the dictionary, e.g. the
     correction key or entity id) to confirm the audit row landed;
   - recompute the post-correction metric (e.g. backlog and delivered counts).
5. **Decide the status enum** strictly by the success rule, and assemble the
   output object (no arrays if the template forbids them). The audit record in
   the answer mirrors the values actually committed.

## Idempotency / safety

- If a pre-check shows the correction already applied (audit key present, value
  already canonical), do **not** write again — report the observed state and the
  status the rule dictates.
- Keep every exploratory query on `/api/sql` (read-only). Reserve
  `/api/sql/transaction` for the single approved change.
