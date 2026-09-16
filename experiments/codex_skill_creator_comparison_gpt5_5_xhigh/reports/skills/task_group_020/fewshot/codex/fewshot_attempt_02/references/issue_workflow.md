# M&A Workbench Issue Workflow

## Common Issue Families

Use this reference after loading the prompt, answer template, and workbench records.

### Closing certainty

Review financing conditions, reverse termination fees, required consents, material-contract consents, HSR clearance, outside dates, remedy covenants, and termination rights.

- Seller-side review usually resists broad buyer optionality and requires remedies or fees only when financing or regulatory risk remains.
- Buyer-side review usually requires closing conditions for material consents, regulatory clearance, and specified material contracts.
- Committee review compares the draft against policy thresholds and includes benchmark support when available.

### Indemnity economics

Review caps, baskets, survival periods, materiality scrapes, special indemnities, escrow or holdback, release mechanics, and knowledge qualifiers.

- Compare cap, basket, escrow, and survival values against preferred and fallback positions.
- Treat missing baskets, escrow agents, release mechanics, or materiality scrapes as issues only when the client-side playbook or prompt requires them.
- Tie escrow release to the relevant survival period unless the record gives a different trigger.

### Transition and carveout terms

Review transition services, stranded costs, clean termination rights, IP or trademark transition, domain redirects, employee transfer process, service credit, PTO allocation, and comparable employment terms.

- Seller-side carveout reviews should protect separation cost recovery, defined service scope, finite duration, IP/domain handoff, and employee transfer certainty.
- Quantify stranded-cost gaps, transition disruption, PTO liability, or revenue at risk only from source records or risk estimates.

### Tax and dispute provisions

Review purchase-price allocation, tax forms, transfer taxes, bulk-sale costs, governing law, forum, and ancillary-document coverage.

- If draft silence conflicts with a required affirmative tax or forum position, classify it as a missing required term.
- Pull the actual allocation method, split, law, and forum from the playbook or policy instead of using assumptions.

### Restrictive covenants and employment

Review non-compete scope, non-solicit duration, covered holders or employee groups, general solicitation exclusions, former-employee exclusions, retention, WARN issues, service credit, PTO, and continuing employee counts.

- Use group-level names when the schema requests groups and stable employee IDs when it requests IDs.
- Avoid broadening covenant coverage beyond the playbook, policy, or deal-specific need.

## Filtering Rules

1. Prefer current draft terms over notes that describe old drafts.
2. Exclude records marked stale, superseded, archived, historical, or distractor.
3. Exclude in-policy terms for escalation-only tasks.
4. Include in-policy terms for deviation-matrix tasks when the prompt says to cover the buyer's or seller's positions across a listed set.
5. Treat absent terms as issues only when the playbook, policy, prompt, or surrounding deal facts make the term necessary.
6. Use the exact issue IDs, final-position codes, redline IDs, blocker types, and enum strings from the active template.

## Priority Ordering

Follow explicit template ordering first. If the task asks for negotiation priority, order by practical closing impact:

1. Closing blockers, regulatory clearance, financing conditions, material consents, and termination rights.
2. High-dollar economics such as indemnity caps, reverse fees, escrow, holdbacks, working-capital adjustments, and quantified special indemnities.
3. Transition continuity, employees, IP/domain transition, material contracts, and operating covenants.
4. Tax allocation, transfer taxes, governing law, forum, and other drafting cleanup.

Within the same tier, sort high risk before medium risk, then by larger quantified dollar impact, then by the template's stable ID order.

## Metric Checks

- Counts should match the arrays actually returned: issue count, high-risk count, medium-risk count, blocker count, consent count, and business outcome count.
- Sum only included dollar components once. Do not double count the same risk estimate through both an issue and a blocker unless the template explicitly asks for both.
- If the template distinguishes low and high exposure, use low/high fields from `risk-estimates`; do not manufacture ranges from negotiation deltas.
- If a source labels a consent as notice-only or post-closing, do not include it in required closing consent totals.
- If a material contract appears both as a consent and as a contract record, use the consent amount for consent-risk totals and annual revenue for material-contract revenue totals.
- Reconcile holder allocations, cap-table shares, and consideration totals where the schema requires full economics.

## JSON Construction

- Build the answer in a scratch file and validate it before responding.
- Keep object keys as shown in the template. For templates that show fixed objects, include each fixed field with `null`, `false`, `0`, or `[]` as appropriate. For templates that show alternative metric shapes, include only fields supported by the chosen metric and task evidence.
- Use plain decimal numbers for percent points, not strings with percent signs.
- Use ISO dates only when a date field is requested.
- Avoid explanatory comments, Markdown, and trailing commas.
