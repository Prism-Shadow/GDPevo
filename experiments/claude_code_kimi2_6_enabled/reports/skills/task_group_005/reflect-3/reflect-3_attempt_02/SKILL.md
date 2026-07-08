# Reusable Solver Guidance

## 1. Read Prompt and Template First
Before fetching any data, read `input/prompt.txt` and `input/payloads/answer_template.json`. The template defines the exact schema, required keys, enum values, and ordering rules. Build the answer skeleton directly from the template so no required field is omitted.

## 2. Preserve Schema Keys and Types
- Copy every top-level key and nested key from the template.
- Use the exact data types specified (string, boolean, integer, float, list, object).
- Enum fields must use only the allowed values; never invent new ones.
- Do not add extra properties unless `additionalProperties` is explicitly allowed.

## 3. Sort IDs Ascending
Any list of business IDs, card IDs, or similar identifiers must be sorted in ascending alphanumeric order, as required by most answer schemas.

## 4. Round USD to Two Decimals
All monetary fields (`*_usd`, `*balance_usd`, `ap_total_usd`, `gl_total_usd`, etc.) must be rounded to exactly two decimal places. Totals and variances must be computed from the rounded line items to avoid drift.

## 5. Use Current API as Source of Record
When the task prompt states that a remote ERP or compliance API is the current source of truth, query that API live. Do not rely on stale local snapshots, CSVs, or JSON payloads that may be out of date. Conversely, if the prompt explicitly designates a local file as the authoritative source, use that file.

## 6. Derive Booleans and Flags from Data
- Boolean summary fields (e.g., `overall_release_ready`, `all_closed`, `reconciliation_ready`, `needs_follow_up`) must be derived from the underlying record state, not hard-coded.
- Flag lists (e.g., `hard_stop_flags`, `bank_mismatch_ids`, `expired_license_ids`) should be populated only when the corresponding condition is confirmed in the source data.

## 7. Validate Totals and Variance Math
- `total_ap_usd` must equal the sum of individual `ap_total_usd` values.
- `total_gl_usd` must equal the sum of individual `gl_total_usd` values.
- `variance_usd` should equal `total_ap_usd - total_gl_usd` (or whatever the prompt specifies).
- `discrepancy_usd` should equal `total_requested_usd - total_approved_usd`.

## 8. Keep Empty Defaults Meaningful
- Use empty lists `[]` for list fields when no items qualify.
- Use empty strings `""` for string fields only when the template explicitly requires a string and no value is available.
- Use `0.0` for monetary totals when no amounts apply.
- Use `0` for integer counts when none exist.

## 9. Map IDs Exactly
Ensure every object keyed by an ID (e.g., `decisions`, `close_results`, `ap_reconciled`, `gl_reconciled`, `hard_stop_flags`, `reportable_ubo_counts`) contains an entry for **every** ID listed in the corresponding `target_business_ids`, `prepaid_card_ids`, or batch scope. Missing or extra keys will break schema compliance.

## 10. Final Review Checklist
- [ ] All required keys present and spelled exactly as in the template.
- [ ] ID lists sorted ascending.
- [ ] USD values rounded to two decimals.
- [ ] Math (totals, variances) reconciles.
- [ ] Enum values match allowed set.
- [ ] Booleans reflect actual data state, not assumptions.
- [ ] No stale snapshot data used when the prompt mandates live API.
