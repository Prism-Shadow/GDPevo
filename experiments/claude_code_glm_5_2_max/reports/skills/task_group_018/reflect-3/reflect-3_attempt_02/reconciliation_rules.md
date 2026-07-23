# Reconciliation Decision Rules

## Source Priority (Highest → Lowest)

| Rank | Source | Controls When |
|------|--------|---------------|
| 1 | Hearing notes / bench notes | Plea, finding, sentence, departure, unsigned-order status, charge amendments |
| 2 | Audit memo / corroboration memo | Identity corrections, counsel-type corrections, stale-value flags |
| 3 | Payment petition / budget form | Balances reported by counter, income, obligations, requested payment amounts |
| 4 | Portal (CMS/case records) | Authoritative identity (DOB, name spelling), case status, structured charge data |
| 5 | Current fee schedule (non-expired) | Current fee amounts override stale queue/worksheet values |
| 6 | Finance queue / worksheet | Default values; these frequently contain stale or draft data |

## Common Conflict Patterns

### Identity Conflicts
- **Scenario**: Finance queue has wrong DOB or misspelled name.
- **Resolution**: Use portal/CMS DOB and name.
- **Resolution source**: `use_cms`
- **Record as**: audit finding with `issue_type: identity`

### Counsel Type Conflicts
- **Scenario**: Queue/worksheet says "PD" but defense memo says "appointed private counsel."
- **Resolution**: Use hearing notes / defense memo.
- **Resolution source**: `use_hearing_notes` or `use_corrob_memo`
- **Impact**: Public-defender user fee is EXCLUDED for appointed-private counsel.
- **Record as**: audit finding with `issue_type: counsel`

### Stale Fee Amounts
- **Scenario**: Finance queue uses old drug-assessment or standard-fine amount from a prior year.
- **Resolution**: Get current amount from `/api/fee-schedules` (entry with `end_date: null`).
- **Resolution source**: `use_fee_schedule`
- **Record as**: audit finding with `issue_type: fee_schedule`

### Departure Label Carried Forward
- **Scenario**: CMS/charge screen shows "dispositional departure" from a draft worksheet but judge stated "no departure."
- **Resolution**: Use hearing notes. Set departure_status = `no_departure` / `none`.
- **Resolution source**: `use_hearing_notes`
- **Record as**: audit finding with `issue_type: departure`

### Case Status When No Final Order
- **Scenario**: Draft worksheet says "disposed/guilty" but the order was not signed and the matter was continued.
- **Resolution**: Case status = `deferred` / `pending`. Do NOT post financial entries.
- **Resolution source**: `use_cms` or `use_hearing_notes`
- **Record as**: audit finding with `issue_type: status`
- **Fee status**: `hold` / `do_not_post_pending`

### Amended Charges
- **Scenario**: Original filed count was a felony (e.g., controlled substance) but state amended to a misdemeanor (e.g., theft).
- **Resolution**: Original count = `dismissed_or_amended_away_counts: 1`. Amended count = `convicted_counts: 1`.
- **Crime-lab fee**: EXCLUDED because the conviction is no longer a controlled-substance count.
- **Record as**: audit finding with `issue_type: status` or specific audit_flag.

### Lab Fee Omitted from Worksheet
- **Scenario**: Judge ordered lab assessment on a CS conviction but the worksheet omitted it.
- **Resolution**: Add the crime-lab fee from the current fee schedule.
- **Record as**: audit_flag `lab_fee_worksheet_omitted`.

### DOB Missing from Bench Card
- **Scenario**: DOB is blank on bench card; case file not in courtroom.
- **Resolution**: Use placeholder `TBD from case file` for DOB. Do not borrow DOB from similarly named defendants.
- **Identity action**: `use_placeholder_verify`
- **Record as**: audit_flag `dob_missing_verify`

## Fee Exclusion Rules

The following fees are EXCLUDED unless the hearing order or current policy explicitly directs them:

| Fee Type | Exclude Unless |
|----------|---------------|
| Account-management fee | Policy `account_fee > 0` and jurisdiction explicitly flags it |
| Collection fee | Referral to collections is documented |
| Late-payment fee | Payment is actually late/defaulted |
| DMV fee | DMV referral is ordered |
| Returned-check fee | A payment was returned |
| Traffic-school fee | Defendant ordered into traffic school |
| Copy/certification fee | Specifically requested |
| Restitution | Restitution order appears in sentencing intake/notes |
| Court-appointed-attorney fee | Explicit order supporting it |
| Court-reporter fee | Explicit order supporting it |
| Crime-lab fee | Only when assessment_code present on convicted count (not amended away) |
| Public-defender user fee | Only when counsel_type = public_defender (NOT appointed_private) |

## Payment Plan Decision Tree

```
Is there a signed sentencing order with financial obligations?
├── NO → No payment plan. Fee status = hold/do_not_post_pending.
└── YES
    ├── Get payment policy for jurisdiction
    ├── Get petition: income, obligations, requested monthly amount
    ├── Compute disposable income = income - obligations
    ├── Is requested amount within [min_monthly, max_monthly]?
    │   ├── NO (below min) → support_classification = below_policy_minimum
    │   ├── NO (above max) → support_classification = above_policy_maximum
    │   └── YES → support_classification = supportable / supported_by_budget
    ├── Is account_fee in policy > 0?
    │   ├── NO → account_fee_treatment = excluded_by_policy, amount = 0.00
    │   └── YES → account_fee_treatment = included_by_policy, amount from policy
    ├── What is restitution priority in policy?
    │   ├── "Restitution before fines and costs" → payment_application_order = restitution_before_fines_costs
    │   └── "Not applicable" → payment_application_order = fines_costs_only
    └── Calculate schedule per SKILL.md step 4 formulas
```
