# Reconciliation and Finance Rules Reference

Detailed rules for auditing, reconciling, and computing financial entries from local materials and portal records. Load this when the SKILL.md summaries are insufficient for a complex conflict.

## Identity Audit Decision Tree

```
Is the defendant DOB in the local worksheet?
├─ YES: Cross-check with portal /api/cases defendant_dob
│   ├─ Match → use that DOB
│   └─ Mismatch → check hearing notes
│       ├─ Hearing note confirms portal → use portal
│       ├─ Hearing note gives different value → use hearing note, create audit finding citing resolution_source
│       └─ No hearing note guidance → use portal CMS record
└─ NO (missing/blank in all sources):
    ├─ Is DOB truly absent from portal too? → use "TBD from case file"
    └─ Portal has it → use portal, no audit flag needed
```

## Counsel Classification Decision Tree

```
What is the counsel_type in /api/cases for the target case?
├─ public_defender
│   ├─ attorney_label_raw = "APD" and hearing/corroborating memo says appointed private?
│   │   └─ OVERRIDE: classify as appointed_private, do NOT apply PD user fee
│   └─ Otherwise → public_defender, apply PD user fee if case is disposed
├─ appointed_private → do NOT apply PD user fee
├─ retained → do NOT apply PD user fee
└─ unknown → do NOT apply PD user fee; flag for verification
```

## Fee Schedule Currency Check

A fee schedule entry is **current** for a case when:
- `jurisdiction_code` matches the case
- `effective_date` <= case disposition_date
- `end_date` is null OR `end_date` >= case disposition_date

A fee schedule entry is **stale** when `end_date` < case disposition_date. Stale amounts must be flagged as audit issues and replaced with current amounts.

## Fee Applicability by Charge Type

| Conviction charge | Fees that apply |
|---|---|
| Controlled substance (POSS-CS) | court_cost + drug assessment (AR-RC) + crime lab fee (AR-UC) + fine if ordered |
| DUI first offense (DWI-1) | court_cost + fine + license suspension consequences |
| Theft (THEFT-CLASS-D) | court_cost + fine |
| Fleeing (FLEEING) | court_cost + fine if ordered |
| Failure to appear (FAIL-APP) | court_cost + fine if ordered |
| Amended to non-drug misdemeanor | court_cost only; no drug/lab assessment |

## Payment Schedule Computation

```
remaining = total_due - down_payment
monthly = approved_monthly_payment

full_payment_count = floor(remaining / monthly)
remainder = remaining - (full_payment_count * monthly)

if remainder == 0:
    total_installments = full_payment_count
    final_payment_amount = monthly
else:
    total_installments = full_payment_count + 1
    final_payment_amount = remainder

first_due_date = disposition_date + first_due_days (adjusted to calendar convention if policy notes specify)
final_due_date = first_due_date + ((total_installments - 1) * interval_months)
return_to_court_date = final_due_date + return_to_court_offset_days
```

## Budget Supportability Check

```
disposable = monthly_income - total_monthly_obligations

check result:
├─ requested_monthly within [min_monthly, max_monthly] AND requested_monthly <= disposable?
│   └─ supportable / supported_by_budget
├─ requested_monthly < min_monthly?
│   └─ below_policy_minimum
├─ requested_monthly > max_monthly?
│   └─ above_policy_maximum
└─ disposable < min_monthly?
    └─ unsupported_by_budget
```

## Standard Exclusion Reasons

| Exclusion reason_code | When to use |
|---|---|
| `no_order_or_policy_support` | Fee/item not supported by any current order or policy |
| `not_part_of_balance` | Fee is external to the case balance (e.g., DMV fee) |
| `not_current_policy` | Fee exists in policy but is not applicable |
| `no_triggering_event` | The event that would trigger this fee has not occurred |
| `stale_schedule` | Fee amount comes from an expired schedule |
| `unsupported_post_disposition` | Fee attempted after disposition without basis |
| `not_in_hearing_order` | Fee not mentioned in the hearing order |
| `missing_identifier` | Field requires an identifier absent from case materials |
| `missing_contact` | Field requires contact info absent from case materials |
| `missing_office_detail` | Field requires office detail absent from case materials |
