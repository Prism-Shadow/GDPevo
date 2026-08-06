# Output Validation Checklist (run before submitting)

Run every item against your final JSON object. The `answer_template.json` is the contract; if any item fails, fix it before emitting.

## A. Template conformance
- [ ] **Top-level keys:** exactly the `required_top_level_keys` (or `top_level` fields) the template lists — no missing, no extra.
- [ ] **Identity/scope fields** (`task_id`, `batch_id`, `roster_id`, `program_code`) set to the template's `required_value` / `constant` / `expected_value`, verbatim and case-correct.
- [ ] **Date fields** use `YYYY-MM-DD` (e.g. `requested_service_date`, `as_of_date`, `received_date`).
- [ ] **Booleans** are JSON `true`/`false`, not `0`/`1` or strings, where the template says `boolean`.
- [ ] **Integers** are integers (no decimals) for all count fields; `null` only where the template allows `integer_or_null` / `enum_or_null`.

## B. Controlled vocabularies
- [ ] Every enum field's value is in that field's `allowed_values` / `allowed` list in the template — **no invented codes, no synonyms, no free text**.
- [ ] Reason / blocker / issue code arrays contain **only** codes from the template's allowed set.
- [ ] Codes that the template defines separately per list (e.g. `blocked_reason_codes` vs `issue_codes` vs `action_codes` vs `reason_codes`) are used in the **correct** list — do not cross-contaminate.

## C. List completeness & ordering
- [ ] **Every in-scope record has a row.** Required-patient-id lists / candidate lists / referral lists include all records for the scope key — no omissions from the 100-cap.
- [ ] **No distractors.** No record whose `batch_id`/`roster_id`/`program_code` ≠ the scope key.
- [ ] **No duplicates** in id lists (unless the template's structure represents a duplicate group).
- [ ] **Ascending-by-id lists** (referral_id, patient_id, transfer_id, group_id, insurance_id) are sorted ascending.
- [ ] **Alphabetical lists** (doc codes, artifact enums) are sorted alphabetically by the enum string.
- [ ] **"Unordered set" arrays** (reason/blocker/issue codes) — order is not meaningful; any order is acceptable but values must be unique within the array.
- [ ] `priority_order` / `action_plan` use the ordering the template specifies (e.g. "highest priority first, non-ready referrals only" with `rank` starting at 1).

## D. Cross-structure consistency
- [ ] **Referral appears in the right buckets.** A referral flagged with `records_missing` in `blocker_sets.records` also carries `records_missing` in its `blocker_codes`/`issue_codes` (and vice versa) — keep per-record codes and the aggregate `blocker_sets` in sync.
- [ ] **Duplicate groups vs cleared list.** Referrals in a duplicate group are handled by `keep_referral_id`/`primary_referral_id`; non-primary duplicates that pass review appear in the cleared list exactly as the template specifies.
- [ ] **Ready-to-schedule / ready_referral lists** contain exactly the referrals whose `readiness_status` is `ready`.
- [ ] **`clinical_code_discrepancy_referrals`** = the set of referrals with a clinical-code discrepancy code; matches the discrepancy list elsewhere.
- [ ] **Chart-action lists** (`ready_referral_chart_needs`) cover exactly the ready referrals; `artifacts_to_create` are the artifacts genuinely missing from the chart bundle.

## E. Summary reconciliation
- [ ] **Cohort totals match row counts.** `total_patients`/`total_referrals`/`total_transfers`/`total_candidates` = number of per-record rows you emitted = SQL `COUNT(*)` for the scope.
- [ ] **Bucket sums = total.** `counts_by_registration_status`, `counts_by_overall_risk`, `counts_by_lifestyle_risk`, `decision_counts`, `status_counts`, `follow_up_counts`, `outreach_counts`, `monitoring_package_counts`, `counts_by_readiness_status`, `counts_by_urgency` — each set of buckets sums to the total.
- [ ] **Cross-tabs sum to total.** `counts_by_urgency_and_status` rows sum to the total and are ordered as the template specifies (e.g. urgency then readiness_status).
- [ ] **Eligible/ineligible split:** `eligible_count + ineligible_count = total_candidates`.
- [ ] **`issue_counts`** reflect the number of referrals/groups/anomalies, not the number of individual codes.
- [ ] Every summary key/bucket the template requires is present (no omitted zero-buckets unless the template allows omission).

## F. Final format
- [ ] Output is a **single JSON object** — valid JSON, parses cleanly.
- [ ] **No prose** before or after the object; no markdown fences; no trailing commentary.
- [ ] **No extra fields** beyond the template's schema.
- [ ] IDs are uppercase exactly as the portal returns them (e.g. `REF0001`, `P040`, `TR0021`).

## G. Completeness cross-check (do this once)
- [ ] Run `SELECT COUNT(*) FROM <table> WHERE <scope_col>='<scope>'` for the primary entity and confirm it equals the number of per-record rows you produced. If it doesn't, you were capped by the 100-row default or included/excluded distractors — re-pull with `?limit=1000` or via SQL.
