# Clerk Operations Skill

## Purpose
Process court clerk docket, financial, and compliance review tasks using a shared
remote clerk-operations API. Produce structured JSON outputs conforming to the
answer template provided in each task.

## Environment
- **Base URL**: `http://34.46.77.124:9018` (from environment_access.md).
- Never use localhost, 127.0.0.1, or env/setup.sh. The remote URL overrides any
  local reference in task text.
- All API calls are read-only GET requests. No authentication is required.

## API Reference

| Endpoint | Parameters | Use |
|---|---|---|
| `/health` | — | Connectivity check |
| `/docs` | — | API documentation |
| `/api/counties` | — | List supported counties |
| `/api/cases/<case_number>` | path | Live case record (status, charges, counsel, etc.) |
| `/api/cases` | — | List all cases |
| `/api/docket?case_number=<case_number>` | query | Docket history entries |
| `/api/financial-obligations?case_number=<case_number>` | query | Live financial ledger (principal, payments, balance) |
| `/api/fees?county=<county>&matter_type=<type>&effective_on=<YYYY-MM-DD>` | query | Active fee schedule for a county, matter type, and date |
| `/api/payment-policies?county=<county>` | query | Installment plan minimums, first-due-date defaults |
| `/api/citations/<citation_number>` | path | Citation identity, violation details, existing plan info |
| `/api/citations` | — | List all citations |
| `/api/hearings?date=<YYYY-MM-DD>&county=<county>` | query | Hearing records for a date and county |
| `/api/attorneys` | — | Attorney directory |
| `/api/stale-exports?county=<county>&name=<export_name>` | query | Stale pre-reconciliation export snapshot |
| `/api/search?q=<text>` | query | Full-text search across records |

## Source Precedence

When the same fact appears in multiple sources, resolve conflicts in this order:

1. **Live API records** (cases, docket, financial-obligations, fees, citations) —
   highest authority, always check last.
2. **Local payload materials** (judge minute cards, bench packets, counsel
   confirmations, hearing notes, cashier adjustment logs, provider notices).
3. **Stale exports / draft finance imports** — lowest authority; use only as
   reference hints. Verify all values against live sources before adopting.

**Rule**: When local payloads and live API disagree on counsel, status, or
financial amounts, use the live API as the source of truth but flag the
discrepancy in the output. When a judge's minute card or bench order clearly
states an outcome (plea, sentence, fee waiver), that controls the final
disposition — but financial amounts still come from the live schedule.

## General Workflow

1. **Read the answer template** first — it defines the exact output schema, enum
   values, and ordering rules.
2. **Read all local payloads** (JSON packets, CSVs, memos) to understand the
   task scope and target records.
3. **Query the live API** for each target case/citation: case record, docket,
   financial obligations, fee schedule (correct county + matter_type +
   effective date), payment policy, and any relevant stale export.
4. **Reconcile** local materials against live records. Identify discrepancies
   in counsel, status, financial amounts, or charge outcomes.
5. **Compute financials** using only the live fee schedule. Exclude candidate
   fee codes not supported by the schedule. Apply ledger credits.
6. **Assemble output** matching the template structure exactly.

## Financial Calculation Habits

- **Currency**: Always round to 2 decimal places. Use standard rounding
  (half-up).
- **Fee schedule lookup**: Use `GET /api/fees?county=<County>&matter_type=<type>
  &effective_on=<disposition_date_or_hearing_date>`. The `matter_type` varies by
  task — common values: `criminal`, `traffic`, `dui`. If the schedule returns
  multiple rows, pick the one matching the charge or matter.
- **Ledger credits**: `GET /api/financial-obligations?case_number=<case>`
  returns `amount_paid` or `total_credits`. Subtract from principal to get
  `corrected_balance_due`.
- **Financial delta**: `corrected_assessment_total - current_ledger_principal`.
  Positive delta = new charges to assess. Negative delta = over-assessment to
  correct.
- **Excluded fee codes**: Candidate codes from local workpapers that are NOT
  supported by the active fee schedule, OR that have no corresponding order
  (e.g., traffic school fee when school not elected, late fee when not ordered),
  go in the excluded/candidate-exclusion list, not the assessed list.
- **Restitution handling**: Restitution is part of the principal total but may
  or may not have a separate admin fee code (`CR-REST-ADM`, `DUI-REST-ADM`).
  Check the schedule. When restitution is $0.00, no admin fee applies.

## Payment / Installment Plan Rules

- **Policy lookup**: `GET /api/payment-policies?county=<county>` returns the
  county's minimum monthly amount and default first-due-date offset.
- **First due date**: When not stated in the bench order or local packet, use
  the policy default (typically 30 days from disposition or the next month's
  first business day after that offset). When stated, use the stated date.
- **Monthly amount**: Must be ≥ the policy minimum unless an ability-to-pay
  petition was approved. When the defendant requests an amount below the
  minimum, verify against any approved petition.
- **Installment math**:
  - `monthly_amount * full_payment_count + final_payment_amount = principal (or balance_due)`
  - `total_payment_count = full_payment_count + (final_payment_amount > 0 ? 1 : 0)`
  - `final_due_date = first_due_date + (total_payment_count - 1) months`
- **Null handling**: When no payment plan applies (`plan_status: "none"` or
  `"not_entered"`), set `monthly_payment_amount`, `final_payment_amount`,
  `first_due_date`, `final_due_date` to `null` and `installment_count` to `0`.
- **Balance-based plans**: When `plan_basis` is `current_balance`, compute
  installments against `corrected_balance_due`. When `original_principal`, use
  the principal before credits.

## Ordering Conventions

- **Case/citation rows**: Always sort ascending by `case_number` or
  `citation_number` (lexicographic on the full string, e.g.
  `23-MAR-01004` < `24-MAR-01004`).
- **Charges within a case**: Sort ascending by `charge_id` (`CHG-001`,
  `CHG-002`, …).
- **Fee components**: Sort alphabetically by `fee_code`.
- **Excluded fee codes**: Sort alphabetically by code.
- **Aggregate lists** (case numbers in `representation_mismatch_cases`,
  `post_credit_case_numbers`, etc.): Sort ascending.

## Filtering Rules

- **Review-needed flag**: When the local packet includes `review_needed:
  false`, exclude that item from the output entirely. These are informational
  only.
- **Queue filtering**: Stale exports often contain records from multiple queues.
  Only include rows whose `queue` or `matter_hint` matches the task's docket
  type (e.g., `mixed_misdemeanor_docket`, not `traffic_context` or
  `compliance_context`).
- **Name-similarity checks**: Ignore records flagged as name-similarity pulls
  (`review_needed: false`) — they are not part of the active review.

## Common Enum Values

### Case/Disposition Statuses
`open`, `probation_active`, `closed`, `deferred`, `dismissed`,
`warrant_recalled_pending_entry`, `needs_review`, `warrant`

### Plea Values
`guilty`, `no_contest`, `not_guilty`, `not_entered`, `deferred_entry`

### Disposition Values
`convicted`, `dismissed`, `deferred`, `pending`, `amended`,
`convicted_no_separate_fee`

### Verdict Values
`guilty`, `not_guilty`, `dismissed`, `deferred`, `not_adjudicated`

### Defense Types
`retained`, `appointed_private`, `public_defender`, `self_represented`,
`unknown`

### Discrepancy Codes (Criminal Docket)
`none`, `attorney_conflict`, `status_conflict`,
`financial_schedule_conflict`, `attorney_and_status_conflict`,
`status_and_financial_conflict`, `identity_conflict`

### Source Conflict Codes (Compliance)
`no_source_conflict`, `live_ledger_vs_packet_receipt`,
`petition_changes_payment_plan`, `packet_service_shortfall`

### Docket Actions
`enter_plea`, `enter_sentence`, `recall_warrant`, `enter_attorney_update`,
`generate_financial_entry`, `needs_supervisor_review`

### Financial Statuses (Compliance)
`paid`, `paid_after_credit`, `current`, `delinquent`, `replan_approved`,
`pending_adjustment`

### Payment Plan Actions
`none`, `keep_existing`, `approve_revised_plan`, `send_return_to_court`,
`post_credit_close`

## Pitfalls

1. **Stale export contamination**: Stale exports may have outdated status,
   counsel, or principal amounts. Always cross-check against the live API and
   local bench materials. Do not propagate stale values into the output.
2. **Nearby citation confusion**: A stale export or ledger may reference a
   similar citation number (e.g., `CIT-LAN-2024-00412` when the target is
   `CIT-LAN-2024-00411`). Do not merge or confuse them.
3. **Candidate fee codes**: Local workpapers often include fees that are not
   supported by the schedule or the order. Each candidate code must be verified
   against the live fee schedule AND the judge's order. Put unsupported codes
   in `excluded_candidate_fee_codes` / `excluded_fee_or_charge_codes`, not in
   the assessed list.
4. **Fee schedule effective date**: Use the disposition/hearing date as the
   `effective_on` parameter, not today's date. Fee schedules can change.
5. **Restitution admin fees**: `CR-REST-ADM` or similar admin fees only apply
   when restitution is ordered (> $0.00). Check the schedule for the exact
   trigger condition.
6. **Probation fee exclusion**: When a bench note says "no separate probation
   setup fee was pronounced," exclude `CR-PROB` / `DUI-PROB` from the
   assessment even if the schedule supports it.
7. **Zero vs null**: `0.0` means a value exists and is zero (e.g., no
   restitution ordered). `null` means the field is not applicable (e.g., no
   payment plan exists).
8. **Receipt not on ledger**: When a cashier adjustment log shows a receipt
   with `posting_status: "not_on_live_ledger"`, the credit must be applied to
   reduce the live balance. The `correction_amount` is positive and reduces
   `corrected_balance_due`.
9. **Warrant recall**: When the bench recalls a warrant, set `recall_warrant:
   true`. This is independent of whether an attorney update is also needed.
10. **Supervisor review**: Route to supervisor when: counsel substitution
    creates a caption mismatch, financial entries replace obsolete batches on
    older cases, or the verification memo requests it.

## Output Conventions

- Return **only** the completed JSON object. No markdown fences, no commentary.
- Use ISO 8601 dates (`YYYY-MM-DD`). Times in `HH:MM` 24-hour format.
- All currency values: numbers (not strings), rounded to 2 decimal places.
- Boolean fields: `true` / `false` (not strings).
- Enforce enum values exactly as specified in the answer template.
- When a template requires `task_id`, use the value specified in the template
  (not inferred from filenames).
- `null` for optional date/number fields that have no value; never use empty
  strings or `0` as a null substitute.

## Task-Type Quick Reference

| Task Pattern | Key Endpoints | Distinctive Fields |
|---|---|---|
| Criminal docket | cases, docket, financial-obligations, fees(criminal), attorneys, stale-exports | `discrepancy_code`, `docket_actions`, `fee_components`, `case_audits` |
| Traffic batch | citations, fees(traffic), payment-policies, stale-exports | `excluded_candidate_fee_codes`, `payment_plan`, `assessed_components` |
| DUI probation packet | cases, docket, financial-obligations, fees(dui), payment-policies, attorneys | `conviction_posture`, `collateral_orders`, `charge_outcomes`, `identity_fields` |
| Mixed misdemeanor review | cases, docket, financial-obligations, fees(criminal), attorneys, stale-exports | `representation_mismatch`, `financial_delta`, `docket_action`, `approved_fee_codes` |
| Compliance review | cases, financial-obligations, payment-policies, stale-exports, docket | `financial_status`, `source_conflict_code`, `community_service_status`, `correction_amount` |
