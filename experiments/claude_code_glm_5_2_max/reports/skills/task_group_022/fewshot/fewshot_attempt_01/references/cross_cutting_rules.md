# Cross-cutting correctness rules

Distilled from the answer-template contracts and business definitions common to these scorecards. Treat as a checklist; always defer to the current task's `*_request.json` and `answer_template.json` when they specify something different.

## 1. Output contract fidelity
- `additionalProperties: false` → emit **exactly** the `required` set, no more, no less, exact key casing against the template.
- Respect per-field `type`, `minimum`/`maximum`, `multipleOf`, `pattern`, and `enum`.
- Arrays: honor `minItems`/`maxItems` (often *exactly* N), `uniqueItems`, and the documented ordering note.
- No commentary, no trailing text, no extra JSON documents. One object, parseable.

## 2. Precision and rounding
- Round **only final reported** values, never intermediates used in comparisons or tie-breaks.
- Rates to 4 dp where `multipleOf: 0.0001`; money / units-per-hour / medians to 2 dp where precision/decmials 2; counts as integers (precision 0).
- Carry both an unrounded and a rounded column; use unrounded for ranking/tie-breaks and rounding-boundary decisions, rounded for output.
- Beware boundaries: an unrounded value just below a tier threshold rounds *up* to meet it on display, while the true value does not — let the unrounded value drive tier/eligibility decisions, then round only for output.

## 3. Cohort and denominator discipline
- The eligible population is defined first (production flag, segment/tier/region filter, window, campaign membership). Every downstream metric starts from *that* set.
- Denominators commonly stay the full eligible population even when the numerator excludes rows: incomplete orders remain in the on-time rate denominator; the rework rate denominator is the eligible task count; the severe-active-case rate denominator is the eligible case count.
- When a definition says "distinct", dedupe correctly (distinct orders with ≥1 effective settled logical refund; distinct logical refunds vs distinct linked reversals).

## 4. Complete / on-time / severe causal chains
- "Complete" usually requires existence (≥1 physical shipment) **and** an all-quantifier (every physical shipment effectively DELIVERED by cutoff). No shipment ⇒ incomplete, by definition.
- "On time" layers on complete: complete **and** every shipment delivered ≤ its own `promised_delivery_at`.
- "Severe exception" is an OR across clauses; implement each clause and note that a missing precondition (e.g. no shipment promise) makes *that* clause unsatisfied, not the whole definition. Watch "completed with any shipment delivered > 24h after its promise" as a distinct clause from the incomplete variants.
- Recompute severe rate from your severe-count and the eligible denominator for the status tier — do not infer it.

## 5. Boundary operators
- Window boundaries: trust `inclusive`/`INCLUSIVE` and provide `<=` ends; otherwise open. `as_of_cutoff` comparisons use `<= cutoff`.
- "Strictly before" (`<`) is strict — encode exactly. `due_at strictly before the state cutoff` excludes `due_at = cutoff`.
- SLA "exceeds" means strictly greater than the threshold; time-at/below threshold is not a breach.
- Unresponded/active-at-cutoff clocks: an unresponded case or an active case uses active-elapsed-time **at the cutoff** as its clock value, not a null.

## 6. Ordering and tie-breaks (frequent trap)
- Always read the template's ordering note and replicate it in SQL `ORDER BY`, including secondary/tertiary keys.
- Common patterns: rate asc → label asc; metric desc → code/id asc; count desc → count desc → id asc. Limits are "top N" with the documented tie-breaks — do the `LIMIT` server-side.
- For "worst/lowest/best N" outputs, confirm `row_count == N` after the query; ties beyond N are dropped per the documented tie-break (record if you consciously break a tie, but prefer the documented key).

## 7. Decision-tier if/else chains
- Tiers (HEALTHY/WATCH/CRITICAL; LOW/MODERATE/HIGH; STABLE/PRESSURED/AT_RISK; CONTROLLED/ELEVATED/SEVERE) are checked top-to-bottom; pick the **first** whose condition holds; "otherwise"/"otherwise" / "All other outcomes" is the last bucket.
- Each tier's condition references metrics computed for *this* task. Two-threshold tiers (e.g. "rate ≥ X **and** other rate < Y") require both; "LOW conditions are not both met" carefully inverts the conjunction.

## 8. Money and FX
- Monetary minors are the smallest unit of the row currency; FX is USD per currency unit. FX is USD per currency unit. Convert each amount at the rate for its own `service_date` and currency.
- When comparing two monetary values (e.g. effective settled refund vs order gross), convert both to USD at the **same** basis/date specified by the policy before comparing.
- Sum minors in their currency, convert, then round to display precision last.
- Reversals: pair reversals back to the refunds they undo; "effective settled" = settled and not (fully) reversed per the reversal-linking definition.

## 9. Null / empty handling
- Explicitly handle missing sub-entities (no shipment, no promise, no response) — they change truth value, not just null a number.
- Use `COALESCE`/`IS NULL`/`NOT EXISTS` rather than assuming non-null.
- For rates with a possibly-zero denominator, confirm the cohort is non-empty; if a sub-population (e.g. a warehouse region) is empty its rate is 0 and sorts accordingly — verify against the template's `minimum`.

## 10. Write (correction) tasks
- **Minimal canonical field only**: change exactly one canonical column on exactly one business row (`carrier_scans` or `inventory_movements`); never raw values, source-identity fields, or unrelated rows.
- Exactly one `correction_audit` INSERT with all audit columns, using the request's `audit_id`, `correction_key`, `reason_code`, `actor`, `corrected_at`.
- One `/api/sql/transaction` with `expected_total_changes` matching the guarded UPDATE's affected rows.
- Successful `APPLIED` requires: transaction reports exactly 1 business row + 1 audit row committed **and** a post-change read-only query confirms the new canonical value (and recomputed backlog counts). Anything else → `NOT_APPLIED` reporting *observed* results, never a guessed APPLIED.
- Report `old_value`/`new_value` as strings per the template.

## 11. Self-reconciliation
- Where definitions imply it, assert identities: `eligible = complete + incomplete`; `effective_logical_refunds − effective_reversals` relations; list lengths vs aggregate counts. Resolve any mismatch before writing `answer.json`.
- Re-run lists' counts independently and confirm ordering matches the template note.
