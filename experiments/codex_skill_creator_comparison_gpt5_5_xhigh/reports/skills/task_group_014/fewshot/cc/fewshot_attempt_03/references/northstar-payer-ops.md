# Northstar Payer-Ops Reference

## Environment Access

Use the base URL and credentials provided by the active task. SQL calls use:

```bash
curl -sS -X POST "$BASE_URL/sql/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sql":"select ..."}'
```

The endpoint expects the JSON key `sql`. Keep SQL predicates scoped to task-provided IDs or IDs discovered from the target case. Do not query broad tables just to browse.

Useful business access patterns:

- `GET /api/cases/{case_id}` returns a joined case bundle: case fields, member and plan fields, provider, request lines, documents, document facts, case criteria, authorizations, appeals, assistance screens, drug trials, P2P events, and claims with claim lines when present.
- `POST /sql/query` is useful for `payment_benchmarks`, `service_margin`, `policies`, and `policy_criteria` when these are not included in the case bundle.
- `GET /api/documents/{document_id}`, `GET /api/policies/{policy_id}`, and similar endpoints can fill targeted gaps when the case bundle names a specific linked ID.

## General Mapping Rules

- Start from the answer template's required keys and build a checklist. Every required key must be explained by a prompt value, task-context value, environment record, or deterministic derivation.
- Preserve required list ordering:
  - Document IDs: use the ordering requested by the template, often ascending ID.
  - Claim lines: use claim line order from the environment.
  - Queue rows: use the `queue_row_ids` order from task context.
  - Template choice order: use it for lists of unresolved factors when the template says so.
  - Alphabetical order: apply only when the template requires it.
- Normalize comma-separated environment fields into arrays when the template expects arrays.
- Use JSON `null` for absent modifiers or optional dates when the template allows null. Do not use empty strings for null-like values.
- Round only at the output boundary. Currency is normally two decimals; ratios use the precision specified by the template.
- Use environment status and criteria fields as the primary basis for results, then use documents, facts, notes, and task memos to resolve packet gaps or routing details.

## Basis Audit

Most Northstar templates require:

- `source_precedence`: choose the enum that matches the business conflict being resolved.
- `controlling_record_ids`: records that directly determine the answer, in operational evidence order.
- `exception_record_ids`: gaps, stale records, unsupported criteria, missing packet items, or rejected sources that explain exclusions or adverse routing.
- `precedence_record_order`: highest-priority basis records first; include the controlling and exception records that best explain the result.

Common source-precedence choices:

- `current_clinical_records_over_stale_export`: current clinical documents and plans of care control over stale exports.
- `payer_appeal_before_manufacturer_assistance`: payer appeal eligibility, deadline, criteria, and packet gaps control before assistance intake.
- `effective_benchmark_by_plan_modifier_and_date`: current benchmark rows matched by payer, plan type, service domain, CPT, modifier, and service date control over stale schedules.
- `new_patient_specific_p2p_information`: the completed P2P event controls whether new patient-specific information changes the review.
- `margin_threshold_then_charge_sensitivity`: below-threshold payer-service issues control before charge-sensitive monitoring rows.
- `appeal_deadline_then_clinical_then_payment_integrity`: when a task spans appeal routing, clinical status, and payment integrity, resolve appeal timeliness and route first, then clinical merits, then payment correction details.

Use concise IDs, not explanations, inside audit arrays. Put explanatory reasoning into your private notes, not the final JSON unless the template requests it.

## Prior Authorization Determination

Use this branch for UM nurse summaries and similar authorization decisions.

1. Fetch the target case bundle.
2. Use `case_criteria` results for the required `criteria_results` keys. Do not recompute a criterion differently unless current facts clearly supersede a stale or excluded record.
3. Use current documents and document facts that support the criteria as evidence. Put stale or unrelated documents in the excluded list when the template asks for exclusions.
4. Pull authorization fields from the authorization record: auth number, approved units, start/end dates, approved CPT list, and modifier.
5. Route from criteria and authorization status:
   - all required criteria met and an approval authorization exists: nurse approval / approval-style letter / issue approval.
   - missing or unclear pend-type criteria: pend for information.
   - deny-type criteria not met or out of nurse scope: use the template's adverse or medical-director route.
6. Keep evidence and excluded document lists in the order required by the template.

## Pharmacy Appeal and Assistance

Use this branch for drug coverage appeals, coverage exceptions, and manufacturer assistance intake summaries.

1. Fetch the case bundle and identify the appeal record. Use appeal fields for appeal path, expedited flag, appeal deadline, owner, and open/closed outcome.
2. Map expedited status from appeal path or expedited attestation. Standard or "not requested" attestations are not expedited.
3. Use `case_criteria` for the criteria result map. Partial failure evidence remains `partial` when some required trials are documented and others are unsupported.
4. Classify drug trials:
   - documented trials go in `documented_failures`.
   - undocumented trials, referenced trials without fill evidence, and insufficient contraindication records go in `undocumented_or_insufficient_failures`.
   - Normalize medication names to lowercase and sort as required by the template.
5. Required packet items come from the template choices, appeal notes, policy criteria, and assistance screen requirements. Payer appeal items come before assistance items.
6. Missing packet items include criterion gaps, missing trial/fill evidence, and assistance missing fields. Preserve the template's gap-order instruction.
7. Assistance mapping:
   - no assistance screen: program and status are `not_applicable` when allowed.
   - complete or ready screen with no missing fields: `eligible_ready`.
   - eligible screen with missing fields: `eligible_missing_information`.
   - ineligible screen: `not_eligible`.
8. Next action favors closing information gaps before filing or submitting. If appeal and assistance are both ready, use the combined or submit action allowed by the template.

## Claim Repricing and Payment Integrity

Use this branch for claim correction packets and benchmark repricing.

1. Fetch the target case bundle or claim record and collect claim header, claim lines, member plan type, payer, service domain, and service dates.
2. For each claim line, query `payment_benchmarks` using payer, plan type, service domain, CPT code, modifier with null-safe matching, and service date between effective start and end.
3. If multiple benchmark rows match, prefer the row linked to the target scenario or current source/version. Do not duplicate equivalent benchmark rows in audit IDs.
4. Reject benchmark rows outside the service date range or rows identified as stale by the claim status, document facts, or policy context.
5. Compute:
   - `correct_allowed_amount = benchmark.allowed_amount * line.units`
   - line delta as corrected allowed minus paid amount
   - `correct_upward` when corrected allowed is greater than paid
   - `correct_downward` when corrected allowed is less than paid
   - `no_change` when equal
   - totals as sums of source paid amounts and computed allowed amounts
6. Use the template's instruction for whether `recovery_amount` is signed, absolute, underpayment, or overpayment. If it says underpayment when corrected allowed is greater than paid, use corrected allowed minus paid.
7. `benchmark_source`, `benchmark_version`, and stale rejected source come from the selected current benchmarks and rejected stale source.
8. List lines in claim-line order and use JSON null for absent modifiers.

## Peer-to-Peer Final Summary

Use this branch for completed medical-director P2P summaries.

1. Fetch the target case bundle and identify the completed P2P event.
2. Use the request line for requested CPT and the P2P event for outcome and final status.
3. Use case criteria for required criteria results. Unresolved criteria are criteria that are `not_met` or `unclear`, ordered as the template requires.
4. `new_information_changed_review` is true only when the P2P supplies new patient-specific evidence that materially changes a criterion or outcome. A repeated clinical argument without new supporting facts does not change review.
5. For PET-over-SPECT tasks, compare the template's PET factor choices with documents and P2P new-information text. Missing factors are unsupported choices in template order.
6. For adverse final results, choose the denial-style letter allowed by the template, recommend the lower-acuity or policy-preferred alternative when the policy context names one, and calculate the internal appeal deadline from the adverse determination date plus the plan appeal window stated in the prompt or memo.
7. For approvals or overturns, use approval-style letter fields and null appeal deadline when no adverse deadline applies.

## Therapy Margin Queue

Use this branch for UM-finance margin queues and service-margin summaries.

1. Use only `queue_row_ids` named in task context. Query `service_margin` by those IDs and return rows in the same order.
2. Compute per row:
   - `total_cost = variable_cost + fixed_cost_allocated`
   - `margin = net_revenue - total_cost`
   - `revenue_to_cost_ratio = net_revenue / total_cost`
   - `below_threshold = revenue_to_cost_ratio < threshold`
   - `charge_sensitive = row charge_sensitive flag as boolean`
3. Recommended action:
   - below threshold: `payer_contract_review`
   - otherwise charge sensitive: `monitor_charge_sensitive`
   - otherwise: `monitor_no_action`
4. `below_threshold_segments` contains payer segments for below-threshold rows, sorted by the template rule.
5. `charge_sensitive_segments` contains payer segments for non-below-threshold rows flagged charge sensitive, sorted by the template rule.
6. Top issue is the below-threshold row with the largest dollar gap to the threshold. Use the template's enum format for the segment/CPT label. If no row is below threshold, use the template's no-issue value and a zero gap if a numeric gap is required.
7. `gap_to_120pct` or similarly named fields are `threshold * total_cost - net_revenue` for the top below-threshold issue, rounded to the requested precision.

## Final JSON Check

Before answering:

- Compare top-level keys with the template and remove extra fields when the template disallows them.
- Confirm every enum value appears in the template choices.
- Confirm list order, numeric rounding, date format, and null handling.
- Confirm audit arrays cite environment record IDs or template-recognized gap IDs, not prose.
- Return one valid JSON object and nothing else.
