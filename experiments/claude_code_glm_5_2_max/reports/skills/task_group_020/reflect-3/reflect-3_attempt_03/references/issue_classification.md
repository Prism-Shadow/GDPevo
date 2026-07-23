# Issue classification rules

## Side-aware direction

The playbook `preferred_position` is the side's ideal; `fallback_position` is the walk-to line.
"Exceeds" vs "below" is judged **from the client's perspective** — does the draft move the
economics against your client past the fallback?

| Term family | Seller wants | Buyer wants | Draft past fallback → status |
|---|---|---|---|
| indemnity cap (% PP) | lower cap | higher cap | seller: `draft_exceeds_playbook` when draft > fallback; buyer: `draft_below_playbook` when draft < fallback |
| escrow / holdback (% PP, months) | smaller / shorter release | larger / longer / holdback | seller: `draft_exceeds_playbook`; buyer: `missing_required_term` or `draft_below_playbook` |
| survival (months) | shorter | longer | seller: `draft_exceeds_playbook`; buyer: `draft_below_playbook` |
| materiality scrape | (varies) | full scrape preferred, breach-only fallback | buyer: `draft_below_playbook` when only breach-only |
| reverse break fee / RTF | seller wants a buyer RTF | buyer wants cap on its own RTF | absence → `missing_required_term`/`add` for seller side |
| financing condition | seller: reject condition | buyer: condition acceptable | seller: `out_of_policy` if condition present without fee |
| transition services (months) | shorter, cost-plus | — | seller: `draft_exceeds_playbook` when draft months > fallback |
| customer-consent termination right | seller: no termination right | buyer: wants consents as conditions | seller: `out_of_policy`; buyer: `draft_below_playbook` if draft excludes payer gateways |

### `issue_status` enum (confirm against each template; the standard set is)

`in_policy`, `out_of_policy`, `missing_required_term`, `draft_exceeds_playbook`,
`draft_below_playbook`.

### `recommended_action` mapping

- `missing_required_term` → `add`
- `draft_exceeds_playbook` / `draft_below_playbook` / `out_of_policy` → `revise`
- `in_policy` → `accept`
- playbook `required_action` says "Escalate" → `escalate`, or `approve_with_conditions` /
  `reject` for committee memos

## "Missing required term" — only when the facts justify it

The prompt says: flag an absent protective term as `missing_required_term` **where the surrounding
deal data shows the term is needed**. Do not flag every template ID that lacks a draft term. Use
the transaction type and deal facts:

- **Carveout APA** → required: Section 1060 allocation, transfer-tax split, IP/trademark/domain
  transition, TSA scope/duration/fees (with clean termination), outside-date extension, governing
  law/forum. Each is `missing_required_term` with `recommended_action: add`.
- **Stock purchase (SPA)** → required: D&O tail (a defined multi-year tail, with cost allocated to
  seller or as a purchase-price reduction), restrictive covenants for founders/executives,
  service-credit + PTO allocation, escrow/holdback when survival is at the short fallback. Pull the
  exact tail period and cost allocation from the workbench when present; do not assert a number that
  isn't in a source record.
- **Public-company merger** → fiduciary out (superior proposal + intervening event triggers, 5
  business-day match right), MAE carveouts (limited to general economic/financial-market and
  natural-disaster/terrorism), RW survival cap, RTF within policy.
- A missing term is *not* required (do not flag) when the deal type doesn't implicate it or when
  the surrounding data shows the risk is absent.

## Common issue → source mappings

| Issue | Draft term category | Playbook/policy category | Notes |
|---|---|---|---|
| FINANCING_CONDITION / financing | `financing_condition` | `financing_condition` | boolean draft; fallback is a reverse break fee (% EV) |
| REVERSE_BREAK_FEE / RTF | `reverse_termination_fee` | `reverse_termination_fee` | % of equity/enterprise value |
| INDEMNITY_CAP / indemnity_cap_and_basket | `indemnity_cap` | `indemnity_cap` | % PP; note any special indemnity $ |
| INDEMNITY_BASKET | (often absent) | — | `basket_status: not_found_in_current_records` when absent |
| SURVIVAL_PERIOD / survival_and_knowledge | `survival_period` | `survival_period` | months; track fundamental vs general |
| ESCROW / escrow_holdback_release | `escrow` | `escrow` | % PP + release months; release_trigger |
| MATERIALITY_SCRAPE | `materiality_scrape` | `materiality_scrape` | NONE / BREACH_ONLY / FULL_BREACH_AND_DAMAGES |
| EMPLOYEE_CONTINUITY / employee_service_credit | `employee_transfer` / `employee_service_credit` | same | cite EMP ids, PTO, service-credit, field-selection |
| TRANSITION_SERVICES / TSA | `transition_services` | `transition_services` | months + fee model + stranded overhead |
| TAX_ALLOCATION / SECTION_1060 | (absent in carveout) | — | `mutually_agreed_section_1060` |
| GOVERNING_LAW_FORUM | (often absent) | — | Delaware + Court of Chancery / federal |
| CONSENT_CONDITION / consent_closing_condition | `consent_closing_condition` | same | contract count; note excluded payer gateways |
| HSR_COVENANT / hsr_condition | (regulatory record) | — | regulatory_clearance blocker |
| fiduciary_out | `fiduciary_out` | `fiduciary_out` | removed triggers → `missing_intervening_event_trigger` |
| mae_carveouts | `mae_carveouts` | `mae_carveouts` | excess_count = draft − threshold |
| rw_survival | `rw_survival` | `rw_survival` | fundamental_months vs general_months vs max |

## Benchmark position

Compare the draft value to the benchmark's `median_value` and `upper_quartile` for the matching
`category`:

- draft ≤ median → `at_or_below_median`
- median < draft < upper_quartile → `between_median_and_upper_quartile`
- draft == upper_quartile → `at_upper_quartile`
- draft > upper_quartile → `above_upper_quartile`
- no benchmark applies → `not_applicable`
