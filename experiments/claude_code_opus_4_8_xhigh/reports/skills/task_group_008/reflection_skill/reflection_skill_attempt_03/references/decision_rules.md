# Enum decision rules

Use the exact enum spellings from the task's `answer_template.json` `fields` block — it is authoritative.
Below are the decision rules that reproduce the gold enums. Where a rule is inferred from a single
verified example, that is flagged so you re-derive it from the facts rather than copying blindly.

## Roth conversion / RMD (`roth_conversion_rmd`)

`recommendation` is driven by whether staged conversion produces positive RMD-tax savings, not by RMD
proximity. In both verified cases (RMD 7 years out and RMD 1 year out) the answer was identical:

```
primary_action = STAGED_ROTH_CONVERSION    when rmd_tax_savings_through_horizon > 0 and there is
                                           bracket headroom to convert (annual_conversion_amount > 0)
suitability    = SUITABLE                   when savings are positive and conversions are bracket-capped
risk_flag      = TAX_BRACKET_MANAGEMENT     because the plan is sized to fill (not overflow) the bracket
```

Reach for the other enum values only when the facts clearly demand it:
- `DEFER` / `NO_CONVERSION`: if there is no bracket headroom (`bracket_headroom <= 0`, so
  `annual_conversion_amount <= 0`) or savings are not positive.
- `LIQUIDITY_CONSTRAINT`: if the client lacks outside cash to pay the conversion tax.
- `RMD_NEAR_TERM`: do NOT default to this just because RMDs start soon — the verified near-RMD case
  (RMD next year) still scored `TAX_BRACKET_MANAGEMENT`. The bracket-capping rationale dominates.

> Blind error corrected: a near-RMD client was mislabeled `BORDERLINE` / `RMD_NEAR_TERM`. Positive
> bracket-capped savings → `SUITABLE` / `TAX_BRACKET_MANAGEMENT`.

`heir_tax_profile`: from Roth share at horizon (see formulas.md): `>=0.70 MOSTLY_TAX_FREE`,
`<=0.30 MOSTLY_TAXABLE`, else `MIXED_TAXABLE_AND_TAX_FREE`.

## ILIT / Crummey (`ilit_crummey_implementation`)

Two binary risk dimensions:
- **Exclusion shortfall**: `premium_gap > 0` (premium exceeds annual-exclusion capacity).
- **Three-year lookback**: `is_existing_policy_transfer == true` (an existing policy is being
  transferred into the ILIT, triggering the IRC §2035 3-year inclusion lookback).

```
risk_flag / estate_inclusion_risk:
  no shortfall, no transfer   -> LOW_IF_FORMALITIES_MET
  shortfall, no transfer      -> EXCLUSION_SHORTFALL
  no shortfall, transfer      -> THREE_YEAR_LOOKBACK
  shortfall and transfer      -> THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL

primary_action:
  LOW_IF_FORMALITIES_MET                       -> FUND_WITH_CRUMMEY_NOTICES
  EXCLUSION_SHORTFALL                          -> USE_LIFETIME_EXEMPTION_FOR_SHORTFALL
  THREE_YEAR_LOOKBACK                          -> USE_NEW_POLICY_OR_ACCEPT_LOOKBACK
  THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL  -> DISCLOSE_LOOKBACK_AND_USE_EXEMPTION

suitability:
  LOW_IF_FORMALITIES_MET                       -> SUITABLE_WITH_ADMINISTRATION
  single risk present (shortfall OR lookback)  -> BORDERLINE
  both risks present                           -> NOT_SUITABLE
```
`estate_inclusion_risk` equals `risk_flag` for the same client. `dedicated_bank_account_required` is
always `true`. (Verified clean case: no shortfall, no transfer → LOW_IF_FORMALITIES_MET /
FUND_WITH_CRUMMEY_NOTICES / SUITABLE_WITH_ADMINISTRATION.)

## Trust comparison GRAT vs CRAT (`trust_comparison`)

Driven by the controlling goal facts `family_transfer_priority` and `philanthropic_intent`:

```
preferred_strategy:
  family_transfer_priority == "high" and philanthropic_intent != "high"  -> GRAT
  philanthropic_intent == "high" (and dominates family transfer)         -> CRAT

rationale_code:
  GRAT preferred -> CHILDREN_TRANSFER_PRIORITY
  CRAT preferred -> PHILANTHROPIC_PRIORITY

alternate_role (the non-preferred tool's secondary role):
  GRAT preferred -> SECONDARY_CHARITABLE_TOOL
  CRAT preferred -> SECONDARY_FAMILY_TRANSFER_TOOL

crat.family_transfer_fit:
  GRAT preferred (family is the priority, CRAT is charitable) -> LOW
  otherwise scale MODERATE / HIGH with family-transfer suitability of the CRAT
```
(Verified: family=high, philanthropic=moderate → GRAT / CHILDREN_TRANSFER_PRIORITY /
SECONDARY_CHARITABLE_TOOL / family_transfer_fit LOW.)

## Estate-liquidity action plan (`estate_liquidity_action_plan`)

```
primary_action:
  life policy present AND preferred trust is GRAT      -> COMBINE_ILIT_AND_GRAT
  philanthropic priority / preferred trust is CRAT     -> CRAT_WITH_LIQUIDITY_REVIEW
  ILIT only (no clear trust transfer)                  -> ILIT_WITH_EXEMPTION_REVIEW

sequencing:
  COMBINE_ILIT_AND_GRAT        -> ILIT_FIRST_THEN_GRAT
  trust choice still open       -> TRUST_DECISION_FIRST
  ILIT only                     -> ILIT_FIRST_THEN_ATTORNEY_REVIEW

risk_flag: same ILIT risk logic as above (shortfall / lookback dimensions).
```

### `action_set` membership (alphabetically sorted output)

Include an action only when its trigger fires. Verified gold for a single, high-family-transfer,
low-philanthropic client with a fully-funded ILIT (premium_gap == 0) was exactly:
`["ATTORNEY_DRAFT_REVIEW", "GRAT_FOR_APPRECIATING_SHARES", "ILIT_CRUMMEY_NOTICE_CYCLE"]`.

```
ATTORNEY_DRAFT_REVIEW          : always (attorney coordination meeting).
ILIT_CRUMMEY_NOTICE_CYCLE      : a life-insurance policy proposed for/owned by an ILIT exists.
GRAT_FOR_APPRECIATING_SHARES   : preferred trust strategy is GRAT (family_transfer_priority high).
CRAT_FOR_CHARITABLE_REMAINDER  : philanthropic_intent is "high" (preferred/secondary CRAT warranted).
                                 EXCLUDE when philanthropic_intent is low/moderate.
LIFETIME_EXEMPTION_ALLOCATION  : include only when lifetime exemption must be tapped — i.e. an ILIT
                                 exclusion shortfall (premium_gap > 0) needing exemption coverage, or a
                                 CRAT/charitable path that allocates exemption. EXCLUDE when premium_gap
                                 == 0 even if the taxable estate is positive.
```

> Blind error corrected: `LIFETIME_EXEMPTION_ALLOCATION` was wrongly added just because the taxable
> estate was positive. It is excluded when there is no exclusion shortfall (premium_gap == 0) and no
> charitable-exemption path. `CRAT_FOR_CHARITABLE_REMAINDER` is excluded when philanthropic intent is
> not high. Re-derive each member from the facts; this list-membership area is the highest residual
> uncertainty, so double-check the trigger conditions against the specific client before finalizing,
> and always sort the result alphabetically.
