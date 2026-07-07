# Task Group 005 Solver Guidance

## 1. Initial Setup
- Read `input/prompt.txt` first to understand the business domain and required API endpoints.
- Read `input/payloads/answer_template.json` to understand the exact output schema.
- Read any additional local payload files (e.g., `.json`, `.csv`) that provide batch context or reference data.
- The environment base URL is `http://34.46.77.124:8005`. Use this as the source of record for all ERP/compliance data.

## 2. Schema Compliance
- Preserve every top-level key from `answer_template.json` exactly; do not add or remove keys.
- Use the exact `required_value` fields when specified (e.g., `task_id`, `batch_id`, `as_of_date`).
- Return only the JSON object; do not wrap it in markdown code blocks or add narrative text.

## 3. Data Ordering
- Sort all ID lists in ascending order (e.g., `business_id`, `claim_id`, `vendor_id`).
- For object keys that map to IDs (e.g., `ap_balance_by_claim`, `decisions`), sort the keys ascending as well.

## 4. Numeric Precision
- Round all USD amounts to exactly two decimal places.
- Use `0.00` for zero balances, not `0` or `null`.

## 5. API as Source of Record
- When the prompt says to use "current" ERP/compliance data, always query the remote API.
- Do not rely solely on local snapshots, CSVs, or cached JSON if the prompt explicitly references current API state.
- Typical endpoints to query include vendor, compliance, claim, bill, payment, and risk endpoints under the shared base URL.

## 6. Decision Mapping
- For enum fields (e.g., `release`/`hold`/`escalate`, `ready_to_send`/`needs_ap_refresh`/`blocked`), use only the allowed values listed in the template.
- For per-ID decision objects, ensure every required ID has an explicit value; never omit a required key.

## 7. List Fields
- Return empty lists `[]` when no items qualify.
- Do not use `null` or omit the key when the template specifies a list type.

## 8. Boolean and Nested Objects
- Use `false` for booleans when conditions are not met.
- For nested objects with required sub-keys (e.g., `close_log_required` with `required` and `ids`), always include both sub-keys.

## 9. Review Context
- Pay attention to review dates, as_of dates, and comparison dates in prompts and templates.
- Use the exact date strings specified; do not substitute today's date.

## 10. Verification Before Output
- Double-check that all `required_top_level_keys` from the template are present.
- Verify ascending sort order on every list and object-key set.
- Confirm all monetary values are rounded to two decimals.
- Confirm no extra properties are added beyond what the template allows.
