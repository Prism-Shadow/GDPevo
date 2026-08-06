---
name: ma-deal-workbench-analysis
description: Produce a structured, judge-conforming JSON answer for an M&A deal-review task served by the deal workbench (draft-term issue registers, SPA closing/economics packages, committee escalation memos, carveout transition reviews, buyer deviation matrices). Use when a prompt asks you to act as buyer- or seller-side counsel for a specific project/deal_id and return only JSON matching a provided answer_template.json.
---

# M&A Deal-Workbench Analysis

You are acting as transaction counsel (buyer- or seller-side, stated in the prompt) for one
specific deal. The prompt names a `deal_id` (a string like `PRJ_<NAME>`) and an
`answer_template.json` that defines the exact output shape, allowed enums, and stable IDs. Produce
**only** a single JSON object conforming to that template — no narrative, no prose outside the JSON.

This skill is the transferable entry procedure. It does not contain any task-specific answers or
final values; every value must be derived from the live workbench for the deal you are given.

## 0. Read the prompt and template first, before touching data

1. Read `prompt.txt` in full. Extract, verbatim:
   - your **client side** (`buyer` or `seller`),
   - the **deal_id** and project name,
   - the **playbook_id** or **policy_id** to compare against (named in the prompt or on the deal
     record),
   - the exact output requirement (which sections the package "must cover"),
   - the per-task unit/precision rules (they vary: "integer dollars", "percent points to two
     decimals", "percent points to one decimal", "holder percentages to four decimals",
     "months as integers", "dates as `YYYY-MM-DD`"). These override any default.
2. Read `answer_template.json` in full. It is the contract. Note:
   - `required_top_level_fields` / `required_output_shape` — must all be present,
   - `allowed_enums` — every enum field must take **exactly** a listed value (case-sensitive),
   - `possible_issue_ids` / `stable_issue_ids` / `stable_redline_ids` — issue and redline IDs are
     **fixed vocabularies**; never invent IDs, and use each stable ID at most once,
   - per-field type rules (`integer or null`, `number or null`, `boolean or null`, `array`).
3. Only one deal_id applies. **Do not** pull records from similarly-named projects.

## 1. Gather every workbench resource for the deal

Fetch the deal record and **all** linked sub-resources. The deal record (`/api/deals/<deal_id>`)
carries a `links` map; fetch each one. A complete pass always includes:

- deal record (`headline_value`, `upfront_cash`, `stock_value`, `milestone_value`,
  `client_side`, `client_name`, `counterparty_name`, `target_name`, `transaction_type`,
  `signing_date`, `meeting_date`, `playbook_id`, `policy_id`, `status`)
- draft terms (`/terms`) — the current negotiated positions, each with `term_id`, `category`,
  `numeric_value`, `unit`, `basis`, `clause_ref`, `staleness_flag`
- playbook rules (`/api/playbooks/<playbook_id>/rules`) — seller `PB_SELLER_A` or buyer
  `PB_BUYER_A`; each rule has `preferred_position`, `fallback_position`, `limit_value`,
  `limit_unit`, `risk_default`
- policy thresholds (`/api/policies/<policy_id>/thresholds`) — when a `policy_id` is set; each
  threshold has `category`, `threshold_value`, `threshold_unit`, `restricted_flag`,
  `approval_required`
- consents, material-contracts, employees, cap-table, regulatory, diligence-findings,
  benchmarks, risk-estimates, notes, documents

The documented API list and the read-only SQL endpoint are described in the environment access
file. Use the web API for per-deal resources; use SQL only for cross-table sanity checks. SQL takes
a `sql` field (a single `SELECT`/`WITH` statement) plus the read-only token; `PRAGMA` and
`SHOW` are rejected. Available tables: `deals, draft_terms, playbook_rules, policy_thresholds,
benchmarks, risk_estimates, cap_table, consents, employees, material_contracts, regulatory,
diligence_findings, deal_notes, documents`.

## 2. Establish the dollar basis for every percentage term

Each numeric draft term and each playbook/policy rule carries a `basis`. Convert percentages to
dollars using the basis stated on that exact record — do not assume a single base for the whole
deal:

- `purchase price` / `equity value` → use `headline_value`
- `enterprise value` → for an APA/merger where headline_value is the total consideration, use
  `headline_value` unless a record states a different figure
- `upfront cash` → use `upfront_cash`
- the term's own `draft_value` text sometimes states the dollar figure directly (e.g.
  "equal to 61.6 million dollars"); cross-check your computed amount against it

`headline_value` is the total deal value. For stock deals, `headline_value = upfront_cash +
stock_value + milestone_value` (verify the identity holds; it does in this workbench). When a
task says "calculate from headline purchase price", use `headline_value`.

All currency is **integer USD** (round half-up). Percent points and months are integers or
decimals per the per-task precision rule. Never emit floats with trailing noise for dollars.

## 3. Classify each issue against the playbook / policy

For every stable issue ID the template offers, ask three questions:

1. **Is there a current draft term?** Match by `category`. If `staleness_flag == "stale"`, the
   term is a **distractor** — exclude it unless the task explicitly wants stale terms. Stale +
   in-policy terms are excluded from escalation registers.
2. **If present, does the draft exceed, fall below, or meet the playbook?** Compare `numeric_value`
   to `limit_value` / preferred and fallback. Direction depends on which side benefits:
   - seller playbook wants caps/escrows/survival **lower/shorter**; a draft **above** the fallback
     is `draft_exceeds_playbook`.
   - buyer playbook wants caps/survival **higher/longer** and full scrape; a draft **below** the
     fallback is `draft_below_playbook`.
   - draft exactly at the fallback can be `in_policy`.
3. **If absent, is the term *required* given the surrounding deal data?** The prompt says: treat
   absent seller-protective (or buyer-protective) terms as `missing_required_term` **where the
   surrounding deal data shows the term is needed** — e.g. a carveout needs Section 1060 allocation
   and transfer-tax split; a stock deal with dispersed holders needs D&O tail and restrictive
   covenants; an SPA with a short survival fallback needs an escrow. Do **not** flag every missing
   template ID as an issue — only those the deal facts justify.

Map each issue's `risk_rating` from the playbook rule's `risk_default` (HIGH/MEDIUM/LOW) where one
exists; otherwise infer from exposure magnitude. Map `business_outcome` to the allowed enum that
best matches the term's economic effect.

`recommended_action`:
- `add` for `missing_required_term`,
- `revise` for `draft_exceeds_playbook` / `draft_below_playbook` / `out_of_policy`,
- `accept` for `in_policy`,
- `escalate` / `approve_with_conditions` / `reject` where the playbook `required_action` says to
  escalate or where committee policy is breached.

## 4. Compute deltas, shortfalls, and exposure

- `delta_to_fallback_*` = draft minus fallback **in the direction of the deviation** (signed so it
  represents the gap to close). For caps/escrows/survival where the draft is worse than fallback,
  this is `draft − fallback` (positive).
- `shortfall_dollars` / `shortfall_to_fallback_usd` / `shortfall_to_preferred_usd` = the dollar gap
  between the draft amount and the (fallback/preferred) amount, always a non-negative integer.
- `required_fee_dollars` / `required_amount` = fallback percent × basis.
- Per-issue `exposure` should cite the matching `risk_estimate` by `estimate_id`
  (`RSK_PRJ_<DEAL>_0x`): closing-certainty estimates pair with termination/financing/consent
  issues; indemnity-leakage estimates pair with cap/survival/scrape issues; transition-disruption
  estimates pair with TSA/carveout issues.
- `quantified_impact_dollars` ties an issue to a concrete source figure (a stranded-cost gap,
  PTO liability, consent amount-at-risk, or top-customer revenue).

## 5. Build the aggregate / summary block last

Aggregates are derived from the issue list and the source tables, not invented:

- **counts** (`issue_count`, `high_risk_count`, `medium_risk_count`, `out_of_policy_issue_count`,
  `draft_below_playbook_count`, `missing_required_term_count`, `closing_blocker_count`) = literal
  counts of the rows you produced.
- **headline value** = `deal.headline_value`.
- **quantified exposure** (low/high): the natural reading is the **sum of the distinct risk
  estimates included** in the package (e.g. closing-certainty + indemnity-leakage), not the same
  estimate re-added once per issue. State which components are `included_exposure_components` vs
  `excluded_exposure_components`.
- **negotiation delta** = the sum of the per-issue dollar deltas/shortfalls you computed.
- **required-closing-consent amount at risk** = sum of `amount_at_risk` over consents with
  `required_for_closing == "yes"`.
- **material-contract revenue requiring consent** = sum of `annual_revenue` over material
  contracts with `consent_required == "yes"`.
- **employee totals** = sum of `count` and sum of `pto_liability` across employee groups.
- **priority order / negotiation priority** = issue IDs ordered highest-leverage first (lead with
  the highest-risk, largest-dollar, or structurally blocking items; e.g. termination economics and
  financing/governing issues before employee/PTO items).

## 6. Closing readiness, blockers, and escalation routing

- A **closing blocker** is any required consent (`required_for_closing == "yes"`), any regulatory
  clearance (`hsr_required == "yes"` → regulatory_clearance blocker), and any material contract
  with `consent_required == "yes"` whose loss would be material. Tag `blocker_type` from the
  template enum and set `must_be_satisfied_before_closing: true`.
- Avoid double-counting: if one customer relationship appears as both a consent and a material
  contract, decide a single primary blocker representation and keep the IDs consistent across
  `required_consent_ids` / `required_contract_ids` and the blocker list.
- **Closing readiness** overall status: `NOT_READY` if any HIGH consent/regulatory blocker is
  unresolved; `READY_WITH_CONDITIONS` if only tradeable indemnity/escrow/survival gaps remain;
  `READY` only if no blockers and no out-of-policy terms.
- **Committee escalation** (policy-based tasks): escalate only terms that are (a) `current` (not
  stale), (b) `restricted_flag == "yes"` or exceeding a `threshold_value`, and (c) require
  M&A-Committee approval. Exclude stale, in-policy, or General-Counsel-only terms as distractors.
  `excluded_in_policy_terms` and `excluded_in_policy_categories` record what you intentionally left
  out and why.

## 7. Match the template exactly, then serialize cleanly

- Include **every** required top-level field and every field in each object — use `null` for
  "not applicable / not found", never omit a key the template lists.
- Every enum field takes a value from `allowed_enums`, exact casing. Stable IDs come only from the
  template's ID lists.
- Percent/month/count fields are typed per the template (`integer or null` vs `number or null`).
  Dollars are integers.
- Sort arrays the way the template's `ordering` instructions specify (e.g. `transition_issues` by
  `issue_id` ascending; `priority_order` by negotiation priority; `required_redlines` by
  `redline_id`).
- Serialize as strict JSON. Watch for set-literal typos in generated code (`{a, b}` is a Python
  set, not a dict — use `{"k": v}`). Validate `json.loads` before submitting.
- Return **only** the JSON object. No markdown fences, no commentary.

## 8. Verification checklist before finalizing

- [ ] `deal_id`, `client_side` match the prompt and deal record.
- [ ] Every required top-level field present; every template-listed object field present (null where
      N/A).
- [ ] Every enum value is in `allowed_enums` (case-sensitive).
- [ ] Every issue/redline/blocker ID is from the template's stable vocabulary.
- [ ] Dollar math reconciles: `headline_value == upfront_cash + stock_value + milestone_value`;
      each `*_amount = percent × basis` (integer).
- [ ] No double-counted blockers/consents; counts equal row counts.
- [ ] Distractor terms (stale, in-policy, wrong-approver) excluded, not invented.
- [ ] Output is a single JSON object, validated, no prose.

## When to use the supporting references

- `references/workbench_resources.md` — the canonical list of deal sub-resources and what each
  contributes to an issue register / closing package.
- `references/issue_classification.md` — side-aware direction rules for
  `draft_exceeds_playbook` vs `draft_below_playbook`, and the "missing required term only when the
  facts justify it" rule, with the common issue→source mappings.
- `references/aggregate_math.md` — the deterministic formulas for the summary/aggregate fields and
  the exposure-component convention.
