# Classification & Units Reference

Canonical enum vocabulary, status semantics, and unit rules. These are the reusable
schema conventions shared across deliverable types. Always defer to the specific
`answer_template.json` when it narrows a list.

## Enum vocabulary

### `risk_rating`
`LOW` · `MEDIUM` · `HIGH`

### `issue_status` / `status`
`in_policy` · `out_of_policy` · `missing_required_term` · `draft_exceeds_playbook` ·
`draft_below_playbook`

### `recommended_action` / `required_action` / `recommendation`
`delete` · `revise` · `add` · `accept` · `escalate` · `approve` ·
`approve_with_conditions` · `reject`
(Some templates also use redline-specific `redline_action`: `delete` · `revise` · `add`.)

### `business_outcome`
`closing_certainty` · `escrow_economics` · `indemnity_exposure` ·
`restrictive_covenants` · `employee_transition` · `tax_allocation` · `governing_law` ·
`regulatory_efforts`

### Closing / readiness
`overall_status`: `READY` · `READY_WITH_CONDITIONS` · `NOT_READY`
`overall_posture`: `accept_as_drafted` · `revise_before_signing` ·
`escalate_to_business_lead` · `reject`

## `issue_status` semantics by client_side

Classification is from the **client's** perspective, comparing the counterparty's draft to
the **client's** playbook/policy. "Exceeds" and "below" are relative to the client's
preferred/fallback position, not the counterparty's.

**Seller reviewing a buyer's draft:**
- Buyer term is more aggressive than the seller playbook fallback (e.g. larger escrow,
  longer survival, higher indemnity cap, broader termination right) → `draft_exceeds_playbook`.
- A seller-protective term that is absent → `missing_required_term` (e.g. no governing law,
  no Section 1060 allocation, no reverse break fee, no non-compete).
- A seller protection present but weaker than the seller fallback (e.g. reverse break fee of
  0% vs. 6% fallback) → `draft_below_playbook`.
- Term within the seller playbook envelope → `in_policy` (usually excluded from an issue
  register, but include if the template wants the full matrix).

**Buyer reviewing a seller's draft:**
- Indemnity cap / escrow / survival below the buyer's fallback (less buyer protection than
  the buyer would accept) → `draft_below_playbook`.
- A buyer-protective term absent (e.g. no HSR condition, no escrow, no specific contract
  consents) → `missing_required_term`.
- Term at or above the buyer fallback → `in_policy` / `accept`.
- A seller term that overreaches the buyer playbook (e.g. overly broad non-compete imposed
  on buyer) → `draft_exceeds_playbook`.

**M&A Committee escalation (policy-based):**
- Draft term beyond the policy threshold, or a `restricted_flag` category changed from the
  approved form, or `approval_required` and not met → `out_of_policy`.
- Within threshold / non-restricted → exclude (in-policy distractor).

When unsure between `draft_exceeds_playbook` and `draft_below_playbook`, ask: *does the
draft give the client more or less protection than the client's fallback?* More exposure
than the client can accept → exceeds; less protection than the client needs → below.

## Mapping issue → action → outcome (stable defaults)

| Situation | recommended_action | typical business_outcome |
|---|---|---|
| Buyer-favorable term beyond seller fallback | `revise` | varies |
| Required term absent | `add` | matches the term's domain |
| Term weaker than fallback (e.g. 0% break fee) | `add` (or `revise` if a stub exists) | `closing_certainty` |
| Term within playbook | `accept` | — |
| Restricted policy category breached, severe | `reject` | — |
| Restricted policy category breached, curable | `approve_with_conditions` | — |

These are starting points; the workbench `risk_default` and `required_action` on the
playbook rule/policy threshold override them.

## Units and rounding

| Quantity | Rule |
|---|---|
| Currency | Integer USD. Round half-up; never emit cents. |
| Percent points | Decimal at the precision **the prompt/template states** — tasks differ: two decimals (e.g. `12.50`), one decimal (`8.0`), or whole points. Read the prompt. |
| Holder / cap-table percentages | Decimal fraction to the precision the template states (e.g. `fully_diluted_pct: 0.1850`). |
| Months | Integer months. |
| Days | Integer days (outside-date / extension windows). |
| Dates | `YYYY-MM-DD`. |
| Counts (employees, contracts, carveouts) | Integers. |
| Booleans | `true` / `false` / `null` (null when not applicable). |

### Dollar conversion
`amount = round(percent_points / 100 × base)` where `base = headline_value` unless a
source (term `basis`, risk estimate, finding) explicitly states a different base (e.g.
"upfront_cash", "equity value"). Keep the same base across draft / preferred / fallback
within one issue so the delta is consistent.

### Delta direction
`delta_to_fallback` = gap the client must close = `draft_amount − fallback_amount` taken so
the sign/absolute value matches the template's convention (most templates want the
absolute dollar gap). For shortfall fields (`shortfall_to_fallback_usd`,
`shortfall_to_preferred_usd`), it is `fallback − draft` / `preferred − draft` as positive
shortfalls. Re-read the template's field name to pick the direction.

## Stable-ID conventions

- **Issue / redline IDs**: take from the template's `stable_issue_ids` /
  `possible_issue_ids` / `stable_redline_ids` list. Do not invent new ones.
- **Source record IDs**: cite workbench IDs verbatim. Naming patterns:
  - Draft terms: `TERM_<DEAL_ID>_<NN>`
  - Consents: `CNS_<DEAL_ID>_<NN>`
  - Material contracts: `MAT_<DEAL_ID>_<NN>`
  - Employees: `EMP_<DEAL_ID>_<NN>`
  - Diligence findings: `FND_<DEAL_ID>_<NN>`
  - Risk estimates: `RSK_<DEAL_ID>_<NN>`
  - Benchmarks: `BMK_<DEAL_ID>_<NN>` (or similar)
  - Documents: `DOC_<DEAL_ID>_<NN>`
  - Regulatory: `REG_<DEAL_ID>` / synthetic `REG_<DEAL_ID>_HSR`
- For `missing_required_term` issues, `source_term_ids` is `[]`; still cite any
  non-term source records (e.g. the document or regulatory record that shows the gap) in
  `source_record_ids` if the template has that field.
