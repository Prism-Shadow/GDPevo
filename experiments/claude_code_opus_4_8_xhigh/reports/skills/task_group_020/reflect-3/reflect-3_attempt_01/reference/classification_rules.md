# Classification rules

## Polarity — read `client_side` first

The same number is a win or a loss depending on which side you act for.

| Term | Seller-side client wants | Buyer-side client wants |
|---|---|---|
| Indemnity cap % | lower | higher |
| Escrow % and duration | lower / shorter | higher / longer |
| Survival months | shorter | longer |
| Materiality scrape | none | full (breach **and** damages) |
| Financing condition | absent, or paid for by a reverse break fee | — |
| Consent closing conditions | narrow, only truly required consents | broad, all material consents |
| Transition services | short, fees covering stranded overhead | long, at cost |
| Employee transfer | buyer takes all, assumes accrued PTO | selection rights |
| Regulatory efforts | capped, no hell-or-high-water | stronger efforts covenant |

## `issue_status`

| Condition | Status |
|---|---|
| No current draft term in that category, but the standard (or a pinned template ID) requires one | `missing_required_term` |
| Draft worse than the standard, client is **seller**, value is above the limit | `draft_exceeds_playbook` |
| Draft worse than the standard, client is **buyer**, value is below the limit | `draft_below_playbook` |
| Draft breaches a non-numeric restricted standard (trigger removed, carve-out added, protection waived, exclusion carved out of a condition) | `out_of_policy` |
| Draft meets preferred, or meets fallback where the template offers no better classification | `in_policy` |

For a committee memo the template usually fixes `issue_status` to a single literal —
use it verbatim and let the `excluded_*` fields carry everything you left out.

## `risk_rating`

Inherit it before rating it yourself:

1. Governing `playbook_rules.risk_default` for the term's category.
2. Otherwise the record's own `risk_rating` (`consents`) or `severity`
   (`diligence_findings`).
3. Otherwise: `HIGH` for anything that lets the other side walk or blocks closing;
   `MEDIUM` for economics; `LOW` for boilerplate (governing law, forum, transfer-tax
   split).

Normalize case to the template enum — records store `High`, templates want `HIGH`.

## `recommended_action`

| Situation | Action |
|---|---|
| Term absent and required | `add` |
| Term present but off-standard | `revise` |
| Term present and harmful with no acceptable version | `delete` |
| Draft already at the client's fallback | `accept` |
| Breach of a restricted policy needing a decision body | `escalate`, or the memo's `approve` / `approve_with_conditions` / `reject` |

## Record-flag filters

Apply the flag, do not re-derive it:

| List you are building | Include only |
|---|---|
| Required / closing-condition consents, consent blockers | `consents.required_for_closing == "yes"` |
| Non-blocking notices | `consents.required_for_closing == "no"`, plus `material_contracts.consent_required == "notice only"` |
| Material-contract conditions / blockers | `material_contracts.consent_required == "yes"` |
| Service-credit employees | `employees.service_credit_required == "yes"` |
| WARN-risk employees | `employees.warn_risk` in `{medium, high}` |
| Escalatable policy breaches | `policy_thresholds.restricted_flag == "yes"` **and** `approval_required` == the requested body |

## Aggregates

- `issue_count` / `*_count` = the length of the list you actually emitted.
- Risk counts must recount your own rows, not your intent.
- `required_closing_consent_count` counts `required_for_closing == "yes"` rows.
- Amount-at-risk totals sum only the consents you classified as blocking.
- Material-contract revenue totals sum only consent-required contracts.
- Exposure low/high totals sum each `risk_estimates` category **once**, over the
  categories you included; name the included and excluded categories when the template
  has fields for them.
- Negotiation-delta totals sum the per-issue gaps you emitted — nothing else.

## Deriving quantities the template asks for

| Template field pattern | Derivation |
|---|---|
| `*_amount_dollars` from a percent | `round(base * pct / 100)`, base per the term/rule `basis`, default `headline_value` |
| `delta_to_fallback_*` | draft minus fallback, in the direction that harms the client |
| `shortfall_to_preferred` / `shortfall_to_fallback` | preferred (or fallback) amount minus draft amount |
| `required_fee_dollars` | required fee percent × the basis the rule names |
| `*_pto_liability*` | sum `pto_liability` over the groups in scope |
| `total_employee_count` | sum `employees.count` |
| Holder allocation | `fully_diluted_pct` × cash and × stock separately; both columns must sum to their totals |
| `rtf_excess_amount` / cap excess | (draft pct − threshold pct) × basis |
| Benchmark `position` | compare the matching metric to `median_value` / `upper_quartile`; equal to the upper quartile is `at_upper_quartile`, not `above_upper_quartile` |

## Free-form `*_normalized` / `must_have_terms` objects

Keep them minimal and vocabulary-driven: one key per fact, values drawn from the
template's nested enums (`fee_model`, `tax_allocation_method`, `forum`,
`condition_type`). Use `{}` for a draft that is silent. Do not narrate.
