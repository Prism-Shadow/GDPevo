# answer.json — Output Contract Checklist

Run this checklist against the template before you consider a task done. It is generic to every variant in this skill family.

## Shape
- [ ] The file contains exactly **one JSON object**, parseable as JSON.
- [ ] No prose, no markdown, no code fences, no trailing commentary.
- [ ] No keys beyond those listed in the template's `required` (template has `additionalProperties: false`).
- [ ] Every key in the template's `required` is present.
- [ ] Nested objects repeat the same discipline (additionalProperties, required) one level down.

## Types
- [ ] Every integer field is a JSON integer (no `"5"`, no `5.0`).
- [ ] Every number/rate/amount field is a JSON number.
- [ ] Every enum field uses an exact token from the template's `enum` list.
- [ ] Every id field matches its `pattern` (e.g. `^ORD-[0-9]{6}$`, `^CASE-[0-9]{6}$`, `^ACC-[0-9]{4}$`).
- [ ] date-time fields are valid ISO-8601 UTC strings where required.

## Precision / rounding
- [ ] Rates rounded only as final reported values, to the template's `multipleOf`/`decimal_places` (e.g. 4 decimals where `multipleOf: 0.0001`).
- [ ] Amounts rounded to the template's `unit`/`precision`/`decimal_places` (e.g. USD to 2 decimals).
- [ ] Ranking and threshold checks used **unrounded** values; rounding applied only for display.
- [ ] No NaN / Infinity; no negative values where the template sets `minimum: 0`.

## Arrays
- [ ] Array length within `minItems`/`maxItems` (e.g. exactly 2 worst regions, exactly 3 worst accounts, exactly 3 top employees).
- [ ] `uniqueItems: true` arrays have no duplicates.
- [ ] Ordering matches the template's `order`/`ordering` annotation, on the **unrounded** sort key, with the stated tie-break.
- [ ] Required arrays are present even if empty (unless their `minItems` forbids empty).

## Internal consistency
- [ ] Each rate equals its (unrounded) numerator / denominator.
- [ ] Counts that the definitions imply must sum to do (e.g. `effectively_complete + incomplete = eligible` only where the definitions make them complementary; otherwise confirm the relationship the definition actually states).
- [ ] The classification/status tier is the one the request's rule table yields from the **unrounded** metrics, evaluated in the rule order given.
- [ ] The eligible population (denominator) is exactly the scoped cohort — filtered by campaign / account tier+segment+region / warehouse / batch / case-opened window / task-created window as the request specifies.

## Correction tasks only
- [ ] `correction_target` references the single affected source row and entity, the corrected canonical field, and old→new canonical values.
- [ ] `mutation_result.affected_business_rows` and `audit_rows` match what actually committed (typically 1 and 1).
- [ ] `audit_record` carries **all** audit columns, with `reason_code = SOURCE_RECONCILIATION` and the actor/audit_id/correction_key/corrected_at from the request.
- [ ] `backlog_analysis.backlog_delta` equals `post − pre`.
- [ ] `correction_status` is `APPLIED` only if one business row + one audit row committed and a post-change query confirms the new canonical value; otherwise `NOT_APPLIED` with the actually-observed results.

## Final
- [ ] Re-parse `answer.json` to confirm it is valid JSON with no trailing characters.
- [ ] Diff the keys of your object against the template's `required` list one more time.
