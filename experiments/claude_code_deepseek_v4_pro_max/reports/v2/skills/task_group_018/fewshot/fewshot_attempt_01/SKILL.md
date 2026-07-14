# Clerk Operations — Court Docket & Financial Processing

## Overview

Process post-hearing clerk-ready JSON for circuit, justice, and district courts.
Tasks cover criminal plea/sentencing dockets, traffic citation batches, DUI/probation
collateral packets, mixed-misdemeanor corrections, and post-sentencing compliance
reviews. Every task follows a three-layer data model: **live API records**
(authoritative current state), **local packet/payload materials** (hearing-specific
corrections and judge input), and an **answer template** (output schema).

## Environment

All API calls go to the base URL in `environment_access.md` (the
`GDPEVO_ENV_BASE_URL`). Never use localhost or `env/setup.sh` unless the
environment_access file itself points there.

Key endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness check |
| GET | `/docs` | OpenAPI docs |
| GET | `/api/cases` | All case records |
| GET | `/api/cases/<case_number>` | Single case (e.g. `24-BEN-01005`) |
| GET | `/api/citations` | All citations |
| GET | `/api/citations/<citation_number>` | Single citation (e.g. `CIT-LAN-2024-00411`) |
| GET | `/api/hearings?date=<YYYY-MM-DD>&county=<county>` | Docket by date+county |
| GET | `/api/docket?case_number=<case_number>` | Docket entries for a case |
| GET | `/api/financial-obligations?case_number=<case_number>` | Live ledger/financials |
| GET | `/api/fees?county=<county>&matter_type=<type>&effective_on=<YYYY-MM-DD>` | Fee schedule lookup |
| GET | `/api/attorneys` | Attorney directory |
| GET | `/api/payment-policies?county=<county>` | County payment/installment rules |
| GET | `/api/stale-exports?county=<county>&name=<export_name>` | Stale export queue |
| GET | `/api/search?q=<text>` | Full-text search across records |

## Source Precedence (Mandatory Order)

1. **Live API is authoritative** — always prefer live records over any local
   packet material for current state (case status, ledger balance, attorney of
   record, docket history).
2. **Hearing-specific corrections** from the local packet (judge minute cards,
   attorney verification memo, hearing notes, compliance receipts) **override**
   live records only where the packet reflects a *more recent* event than the
   live record's last-updated timestamp. The packet represents what happened at
   the hearing; the live API may not yet reflect it.
3. **Stale extracts** (CSV or JSON in the packet marked "stale") are explicitly
   out of date. Use them only for cross-reference; when they disagree with the
   live API, discard the stale value.
4. **Fee schedules** from the live `/api/fees` endpoint are the only valid source
   for fee amounts. Never hard-code or assume fee amounts — always look them up
   by county, matter_type, and effective_on date.

## Workflow Rules

### Step 1: Identify the matters
- For docket/hearing tasks: query `/api/hearings?date=<date>&county=<county>` to
  get the case list, or read the case numbers from the local packet.
- For traffic batches: read citation numbers from the packet; use the citation
  number as the `account_reference` when the live citation record has no
  separate case number.
- For compliance reviews: cross-reference packet case numbers against live
  financial-obligation and docket records.

### Step 2: Gather live records for every matter
- Call `/api/cases/<case_number>` or `/api/citations/<citation_number>`.
- Call `/api/docket?case_number=<case_number>` for docket history.
- Call `/api/financial-obligations?case_number=<case_number>` for ledger.
- Call `/api/fees?county=<county>&matter_type=<type>&effective_on=<date>` for
  the fee schedule that applies to this matter type and hearing date.
- Call `/api/payment-policies?county=<county>` for installment plan rules.
- Call `/api/attorneys` to verify counsel assignments.

### Step 3: Resolve discrepancies
Compare live records against the local packet materials. Flag conflicts with
controlled `discrepancy_code` or `source_conflict_code` values. Common patterns:
- **Attorney mismatch**: packet counsel confirmation differs from live case
  attorney → `attorney_conflict`; update `final_defense_attorney` to the
  confirmed name.
- **Status mismatch**: packet disposition implies a status the live case doesn't
  show → `status_conflict`.
- **Both attorney and status differ** → `attorney_and_status_conflict`.
- **All three (status, financial, attorney)** → `status_and_financial_conflict`.
- **Packet receipt vs live ledger** → `live_ledger_vs_packet_receipt`.
- **Petition changes payment terms** → `petition_changes_payment_plan`.
- **Service shortfall (CS hours, restitution incomplete)** → `packet_service_shortfall`.
- **No conflict** → `no_source_conflict`.

### Step 4: Compute charge outcomes
For each charge in each case:
- `plea`: one of `guilty`, `not_guilty`, `no_contest`, `not_entered`.
  A charge that was dismissed without a plea entered gets `not_entered`.
- `disposition`: one of `convicted`, `dismissed`, `amended`, `deferred`,
  `convicted_no_separate_fee`. Use `convicted_no_separate_fee` when the charge
  merges into another conviction for sentencing (no separate financial
  assessment).
- `verdict`: `guilty`, `not_guilty`, or `dismissed`.

### Step 5: Determine sentence fields
- `jail_days`: total days imposed.
- `suspended_days`: portion of jail days suspended (can equal jail_days when
  fully suspended).
- `probation_months`: months of supervised probation.
- `community_service_hours`: hours ordered.
- `treatment_ordered`: boolean.
- `restitution_ordered`: dollar amount, 0.0 if none.

### Step 6: Compute financials

#### Criminal (county-specific codes, e.g. Benton CR-*)
Look up the fee schedule for `<county>`, `matter_type=criminal`,
`effective_on=<hearing_date>`. Common criminal fee codes:

| Code | When it applies |
|------|----------------|
| `CR-FILING` | Always assessed (base filing fee per case) |
| `CR-CONV` | Assessed when at least one charge results in conviction (convicted_charge_count > 0) |
| `CR-PROB` | Assessed when probation_months > 0 |
| `CR-REST-ADM` | Assessed when restitution_ordered > 0 (administrative fee) |

**Calculation:**
```
new_principal_total = sum(all applicable fee amounts) + restitution_ordered
corrected_balance_due = new_principal_total - amount_paid_credit
```

#### DUI (county-specific codes, e.g. Gloucester DUI-*)
Look up the fee schedule for `<county>`, `matter_type=dui` (or equivalent),
`effective_on=<hearing_date>`. Common DUI fee codes:

| Code | When it applies |
|------|----------------|
| `DUI-CONV` | Always on DUI conviction |
| `DUI-LIC` | When license suspension is ordered |
| `DUI-PROB` | When probation is ordered |
| `DUI-TREAT` | When treatment referral is ordered |

**Calculation:**
```
principal_amount = sum(all assessed fee code amounts)
current_balance_due = principal_amount - amount_paid_as_of_packet
```

For financial deltas (correction tasks):
```
financial_delta = corrected_assessment_total - current_ledger_principal
```
Positive delta means the ledger is under-assessed; negative means over-assessed.

#### Traffic
Look up the fee schedule for `<county>`, `matter_type=traffic`,
`effective_on=<order_date>`.

**`excluded_candidate_fee_codes`**: fee codes that appeared as candidates (in
the citation record or fee schedule) but should NOT be entered. Common reasons:
- The charge carrying that fee was dismissed.
- The fee is a surcharge for a specific violation that doesn't apply (e.g.
  `TR-SPEED` when the cited speed doesn't meet the threshold, `TR-SCHOOL` when
  not in a school zone).
- `TR-LATE` when the citation was resolved timely.

`assessed_total = sum(assessed_components[*].amount)`

### Step 7: Build payment/installment plans
When a payment plan is ordered:
- `plan_status`: typically `entered_after_disposition` (plan set up post-hearing).
- `monthly_amount`: the regular installment amount per the payment policy or
  court order.
- `first_due_date`: typically ~30 days after the order/disposition date (exact
  rule from `/api/payment-policies?county=<county>`).
- Structure: `full_payment_count` regular payments of `monthly_amount`, then one
  `final_payment_amount` (the remainder).
- `total_payment_count = full_payment_count + 1` (unless final_payment_amount is
  0, in which case `total_payment_count = full_payment_count` and
  `final_payment_amount` is null).
- `final_due_date`: first_due_date + (total_payment_count - 1) months, same day
  of month.

When a plan already exists and is being revised:
- `plan_basis`: use `original_principal` (plan covers the full principal) or
  `current_balance` (plan covers the remaining balance).
- Recompute installment fields from the new terms.

When no plan is needed (paid in full, case closed):
- `payment_plan_action`: `none`, `post_credit_close`, or `keep_existing`.
- Set `monthly_payment_amount`, `installment_count`, `final_payment_amount`,
  `first_due_date`, `final_due_date` all to `null`.

### Step 8: Determine docket actions
For each case, set boolean flags for clerk actions:
- `enter_plea`: true when plea needs to be formally entered on the docket.
- `enter_sentence`: true when sentence needs to be entered.
- `recall_warrant`: true when an active warrant exists and must be recalled.
- `enter_attorney_update`: true when attorney of record changed at hearing.
- `generate_financial_entry`: true when financial obligations must be created or
  corrected.
- `needs_supervisor_review`: true when discrepancies or complex corrections
  require supervisor sign-off.

Or use a combined `docket_action` string:
- `no_update_needed`, `update_status_and_representation`, `financial_adjustment`,
  `enter_disposition_and_assess`.

### Step 9: Compute aggregate/register totals
- Sum principal totals across all matters.
- Sum balance-due totals.
- Count matters needing supervisor review, financial adjustments, warrant
  recalls, etc.
- List case numbers for specific categories (e.g. `representation_mismatch_cases`,
  `post_credit_case_numbers`, `revised_plan_case_numbers`).

## Output Conventions

- **JSON only** — return the completed JSON object matching the answer template
  shape exactly. No markdown wrapper, no explanatory text.
- **Dates**: ISO 8601 `YYYY-MM-DD`. Times: `HH:MM` 24-hour format.
- **Currency**: numbers (not strings), rounded to exactly 2 decimal places
  (e.g. `342.5` not `342.50`; write `0.0` not `0`).
- **Nulls**: use `null` (JSON null) for genuinely absent values, not `0` or
  `""`. Use `0.0` for zero-dollar amounts.
- **Ordering**: when listing case rows, sort by case number ascending
  (lexicographic on the full case number string, e.g. `23-WAS-00144` <
  `23-WAS-01002` depends on the numeric segments — follow the template's
  ordering convention).
- **Enums**: use only the exact enum strings that appear in the answer template
  or training examples. Never invent a new status/disposition/plea/code value.

## Pitfalls

1. **Do not hard-code fee amounts.** Always call `/api/fees` with the correct
   county, matter_type, and effective_on. Fee amounts differ by county and
   matter type.
2. **Stale extracts are not authoritative.** When a stale CSV disagrees with a
   live API response, trust the live API. The stale extract is provided for
   context only.
3. **`convicted_no_separate_fee`** means the charge merges into another for
   sentencing — it's still a conviction but doesn't generate its own fee line.
   Exclude its fee code from assessed components.
4. **Dismissed charges** have plea `not_entered` (unless a plea was formally
   entered before dismissal). Their fees are excluded.
5. **CR-CONV only when there's a conviction.** For deferred dispositions or
   fully dismissed cases, omit CR-CONV.
6. **CR-REST-ADM only when restitution > 0.** If restitution_ordered is 0.0, do
   not include the restitution administrative fee.
7. **Payment plan arithmetic**: `monthly_amount × full_payment_count +
   final_payment_amount` should equal the plan basis amount (principal or
   balance). Verify this invariant.
8. **Citation number as case reference**: when a citation has no separate case
   number in the live record, use the citation number (e.g.
   `CIT-LAN-2024-00411`) as both the `citation_number` and `account_reference`.
9. **Attorney type mapping**: `retained` (private counsel hired by defendant),
   `public_defender` (court-appointed PD office), `appointed_private` (private
   attorney appointed by court, typically paid from a court fund).
10. **`representation_mismatch`**: true when the packet counsel confirmation
    differs from the live case's attorney of record.
