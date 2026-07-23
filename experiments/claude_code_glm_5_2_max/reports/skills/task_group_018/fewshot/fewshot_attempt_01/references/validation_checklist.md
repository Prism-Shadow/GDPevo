# Validation Checklist

Run this against the emitted JSON before declaring the answer complete. Each item names the failure mode it catches.

## Schema conformance
1. **All required top-level keys present** (per `answer_template.json`), and no top-level key that the template does not allow. → catches missing/extra sections.
2. **Every item carries every required key** (per the template's per-item `required_keys`). → catches dropped fields inside arrays.
3. **Every enum field is an exact allowed token**. Never prose ("Not Guilty") where an enum (`not_guilty`) is required; never a token not in the allowed list. → catches enum drift / prose substitution.
4. **Currency is two-decimal numbers** (`150.00`); `0.00` for excluded/empty; `null` only where the template explicitly allows it on a money/date field. → catches `0`, `null`, stringified numbers.
5. **Dates ISO `YYYY-MM-DD`; datetimes `YYYY-MM-DDTHH:MM:SS`**. → catches `MM/DD/YYYY` and bare times.
6. **Lists sorted exactly per the template's ordering rules** (by case_number/citation_number/petition_id ascending; excluded by code ascending; placeholders by field name ascending; apply multi-key sorts in the given order). → catches unsorted output.

## Coverage
7. **Every matter the prompt named appears** in the disposition/case-audit/fee/docket/plan sections as appropriate. → catches dropped targets.
8. **No extra/unprompted matters** appear. → catches leakage from search results or adjacent batches.
9. **Each held/excluded matter has a matching exclusion/hold entry** and zero financials. → catches a held matter missing its `exclusions` row.

## Reconciliation correctness
10. **No stale, archived, prior-year, or "draft" value survives** into a posted disposition, fee item, or total. Each must be corrected to the current schedule/record value or moved to an exclusion section with a reason code. → catches stale leakage.
11. **Counsel classification corrected** where the calendar label conflicted with the corroborating record; PD-user-fee treatment updated to match (excluded for appointed-private/retained). → catches wrong counsel → wrong fee.
12. **Conviction count reflects amendments**; lab/assessment fee present iff the conviction is the controlled-substance count. → catches filed-count-vs-convicted-count and lab-fee mismatch.
13. **Departure label corrected** to the judge's on-record statement (no_departure/top-of-range), or the misdemeanor/pending token where appropriate. → catches stale departure labels.
14. **Finality gating holds**: any matter with no signed order is deferred/continued/pending with zero financials and the hold/exclude docket action — no fine posted, no register entry. → catches posting on a deferred matter.

## Totals and math
15. **Every total equals the recomputed sum of its components** (recompute; do not copy worksheet totals). Posted matters only; held/excluded contribute zero. → catches wrong batch totals.
16. **Installment math self-consistent**: `full = floor(amount_due / M)`; remainder>0 ⇒ `total = full+1`, `final = remainder`; remainder==0 ⇒ `total = full`, `final = M`; `final_due_date = first_due + (total−1) months`. → catches off-by-one installments.
17. **`unsupported_charge_total_included` is `0.00`** when all stale/unsupported lines were excluded. → catches unsupported leakage into the balance.
18. **`total_due` includes restitution only when an order supports it**; payment application order matches policy + petitioner request. → catches unsupported restitution.

## Placeholder discipline
19. **No invented identifiers or contacts anywhere** (SSN, DLN, addresses, phone, attorney, judge, probation office). → catches fabrication.
20. **Every genuinely-missing required form field uses the exact placeholder string** (standard `TBD from case file`) and is recorded in the placeholder section with the matching reason code; placeholders sorted per template. → catches missing placeholder rows / wrong reason codes / prose placeholders.
21. **No value borrowed across parties** (DOB, DLN, address from a similarly-named row). → catches cross-party contamination.

## Final
22. **Output is a single valid JSON object** — no markdown fences, no prose, no trailing commentary. → catches non-JSON output.

## Common failure-mode quick list
- Stale fee amount still in the posted total instead of excluded.
- Fine posted for a deferred/no-order matter.
- "APD" treated as public defender → PD user fee wrongly added.
- Filed CS count used as conviction count (→ lab fee on an amended misdemeanor, or lab fee missing on a CS conviction).
- Batch total copied from worksheet instead of recomputed.
- Last installment count off-by-one (remainder mishandled).
- Enum value emitted as prose, or a token not in the allowed list.
- Invented DLN/address instead of the placeholder.
- Held matter missing its `exclusions` row.
- `unsupported_charge_total_included` left nonzero because a stale line was retained in the balance.
