# Reasoning Rules

## Source Priority

Use the task prompt and answer template as the output contract. Use workbench records as evidence. Use playbook, policy, or committee rules to determine required positions. Use benchmarks and notes as support for recommendation and priority, not as substitutes for operative rules.

Check every record's deal ID. Ignore records from similarly named projects. Exclude stale, superseded, draft-internal, in-policy, or non-committee records unless the template specifically asks to list exclusions.

## Classification

Classify from the client's side:

- Seller-side: flag draft terms that burden seller beyond playbook fallback as `draft_exceeds_playbook`; flag absent seller protections as `missing_required_term`; flag required seller protections drafted below fallback as `draft_below_playbook`.
- Buyer-side: flag buyer protections drafted below fallback or preferred minimum as `draft_below_playbook`; flag absent buyer conditions, escrow, holdback, HSR, consent, material-contract, service-credit, or special-indemnity protections as `missing_required_term`; mark acceptable fallback positions as `in_policy` only when the template calls for an all-position matrix.
- Committee escalation: include only current terms that are out of policy or restricted for committee approval. Exclude in-policy and stale items, and record exclusions only in fields designed for them.

Risk ratings are evidence-driven. Use `HIGH` for closing blockers, HSR clearance gaps, major consents, material-contract conditions, financing certainty gaps, large indemnity/escrow deviations, employee transition failures, or transition/IP/domain risks that can disrupt operations. Use `MEDIUM` for negotiable legal cleanup, survival period deviations, tax allocation, governing law/forum, or fallback positions that still carry legal risk. Use `LOW` for minor or low-dollar records the template still requires.

## Common Issue Logic

Indemnity and escrow:

- Compare cap, basket, scrape, survival, escrow amount, release period, special indemnity, and holdback terms against playbook preferred and fallback positions.
- For seller-side review, excess cap, excess escrow, longer survival, broad materiality scrape, or missing basket usually increases seller exposure.
- For buyer-side review, low cap, missing basket support, short survival, missing materiality scrape, absent escrow/agent/release terms, or unresolved diligence findings usually weakens buyer protection.

Closing certainty:

- Financing conditions are usually seller issues unless paired with an adequate reverse break fee or other closing certainty protection.
- Regulatory facts control HSR and industry approvals. If HSR is required and no clearance condition exists, add or flag the condition. Do not require hell-or-high-water unless the playbook or prompt says so.
- Consents and material contracts must be split into required closing consents, notice-only items, post-closing covenants, and excluded/non-blocking records. Closing blocker arrays should include only records that must be satisfied before closing.

Employees and transition:

- Use employee records for continuing employee counts, service-credit populations, PTO liabilities, WARN risk, retention groups, and field-selection or cherry-pick rights.
- For carveout or transition tasks, review TSA scope, duration, fee model, stranded cost recovery, clean termination rights, trademark/IP transition, domain redirects, and outside-date extensions tied to regulatory timing.

Economics and cap table:

- Allocate cash, stock, milestone, or total consideration using the cap table basis requested by the prompt. Holder percentages may need decimal fractions to four places or percent points; follow the template text exactly.
- D&O tail and transaction expenses are usually covenant/economics fields. If amounts are absent from the workbench, report the specified open or not-quantified status rather than inventing an amount.

Tax and forum:

- In asset deals, look for Section 1060 allocation, Form 8594 consistency, transfer-tax splits, bulk-sale costs, governing law, forum, and application to ancillary documents. Treat draft silence as missing when seller or buyer position requires affirmative language.

## Calculations

Use the correct base:

- If the prompt says headline purchase price, purchase price, equity value, upfront cash, identified findings, or another basis, use that basis.
- If a source record explicitly states a different basis for a metric, use the source basis and describe it in the matching basis field if the template has one.

Apply these formulas:

- Percent amount: `round(base_dollars * percent_points / 100)`.
- Seller delta when draft exceeds fallback: `draft_amount - fallback_amount`.
- Buyer shortfall when draft is below fallback: `fallback_amount - draft_amount`.
- Buyer shortfall to preferred: `preferred_amount - draft_amount`.
- Reverse fee shortfall: `required_fee_amount - draft_fee_amount`.
- Month delta: absolute difference to the fallback or policy threshold in the direction relevant to the client.
- Consent amount at risk: sum required closing consent amounts, not notice-only amounts.
- Material-contract conditioned revenue: sum annual revenue for material contracts requiring closing consent or condition, not excluded notice-only contracts.
- Exposure totals: sum only risk estimate records or issue impacts that the template asks to include; keep low and high totals separate.

Formatting:

- Currency values are integer dollars.
- Percent point precision follows the prompt, often one or two decimals. Whole percent instructions mean no decimal unless JSON number formatting naturally shows one.
- Months are integers.
- Dates are `YYYY-MM-DD`.
- Use `null` for not applicable, unavailable, or non-numeric fields; use `0` only for a measured zero.

## Final Validation

Before responding:

- Parse the JSON locally when possible.
- Verify every object has exactly the fields required by the template, with enum values copied exactly.
- Verify source IDs exist in the current workbench evidence.
- Verify issue counts, risk counts, blocker counts, exposure totals, and priority ranks match the included records.
- Verify missing terms use empty `source_term_ids` and do not cite stale draft terms.
- Verify the final answer contains no commentary outside the JSON object.
