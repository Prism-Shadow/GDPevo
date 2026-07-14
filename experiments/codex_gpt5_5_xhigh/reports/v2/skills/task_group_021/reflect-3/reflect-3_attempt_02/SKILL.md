# AsterOps Data-Quality Audit Skill

Use this skill for AsterOps audit tasks that ask for a single JSON answer using a provided template. The tasks typically involve CRM contacts/campaigns, fleet fuel purchases, logistics cost events, or facilities charges exposed through a remote workbench.

## Remote Environment Workflow

- Use the task-provided remote base URL and start with the catalog. Do not look for local environment source files.
- Prefer filtered API endpoints for the current operational state. Use CSV downloads when the prompt asks for a snapshot/export reconciliation or when the catalog says a shared download is part of the audit.
- Treat every record returned by the relevant endpoint filter as in scope unless the prompt or template gives a narrower business key rule. Background-looking IDs can still be valid in-scope records.
- Keep separate ledgers for raw source rows, effective records, canonical entities, and retained/loadable entities. Most mistakes come from mixing those populations.

## Output Construction

- Return exactly one JSON object and no prose when the prompt requests JSON only.
- Follow the answer template's required keys, controlled enums, field names, and object shapes exactly. Include required zero-valued enum keys.
- Sort ID lists lexicographically ascending unless the template says otherwise. Sort sample/audit rows by the requested key, usually ID or `person_key`.
- For issue-type arrays, use the enum order from the template. For review-reason arrays that say label order, sort alphabetically by enum label.
- Counts are integers. Currency, spend, gallons, and other decimal measures should use the precision requested by the template.

## Effective Record Rules

- Void records are excluded from operational totals and effective counts, but still appear in void/superseded audit lists when requested.
- Amendment records are retained as the effective replacement when valid. The amended original is superseded if it is in scope.
- Invalid records are excluded from corrected totals/effective counts. Common invalid conditions are negative amount, missing amount, invalid unit, and invalid currency.
- Duplicate business-key counts are based on non-void, non-invalid effective candidates after amendment handling unless the template says to count raw duplicate rows.
- CSV snapshot rows do not override current API records. Current API wins for operational totals; stale or legacy CSV-only rows belong in source-delta audit lists.

## Numeric Handling

- Use decimal arithmetic for money. Convert each line to USD using the remote quality-rule rates, round that line to cents, then aggregate.
- Report USD amounts with two decimal places. Do not aggregate unrounded converted amounts and round only at the end.
- For fuel gallons, include effective zero-gallon rows in counts and zero-gallon audit lists unless the template explicitly excludes them.

## CRM Contact And Campaign Rules

- Normalize email by trimming outer whitespace and lowercasing.
- Normalize phone by removing non-digits; preserve country-code digits that appear in the source.
- Suppression is row/member specific: do-not-contact, revoked consent, bounced, and unsubscribed rows are hard blocked. Do not discard an entire duplicate person when an active steward correction supplies a valid canonical contact.
- Contact duplicate resolution favors business source precedence and active steward corrections over simple newest-row selection. `crm_verified` can beat a newer event import; an active `steward_override` can rescue a stale or suppressed duplicate group.
- Campaign duplicate people can have one canonical retained member while noncanonical duplicate member IDs go to manual review. Keep duplicate manual-review IDs separate from hard-blocked/suppressed IDs.
- Domain and segment counts are for retained, qualified, reachable canonical people only. Segment mapping is normalized from raw text into the template enums.

## Alias And Category Rules

- Resolve aliases case-insensitively with substring matching unless a reference says otherwise. When multiple aliases match, use priority to pick the canonical value and record the relevant audit reason.
- Fleet fuel: generic `unleaded` matching a more specific unleaded alias is a trap to audit. Vehicle fuel exceptions remain included in totals but are excluded from mismatch queues.
- Facilities charges: the raw category is the primary category signal. Description aliases that point to a different category are review evidence, not automatic category overrides, unless the task states a priority override rule.
- Unknown aliases map to the controlled `unknown` enum when the reference says so; they are not automatically invalid.

## Quality Counts And Audit Lists

- Read each count description carefully: source-row quality flags count raw rows, while retained/load counts count canonical effective entities.
- Non-USD logistics counts and samples should exclude void and invalid rows; invalid rows are counted under their invalid issue types instead.
- Suppressed-reachable lists are row/member IDs that still have a usable normalized channel even though business rules block them.
- Normalization-change lists should include rows whose nonblank email or phone changes after trimming/lowercasing or digit extraction.
- Top-N city/vendor/lane summaries use the requested measure, descending by value, then ascending by name for ties.

## Common Pitfalls

- Do not throw away records just because their IDs look like background data.
- Do not let CSV-only or CSV-stale records enter current operational totals.
- Do not count blocked, manual-review, or unreachable CRM people in retained audience/domain/segment aggregates.
- Do not include invalid logistics rows in non-USD samples, even if they have a non-USD currency.
- Do not put superseded excluded records in canonical samples; attach superseded evidence to audit lists/counts.
- Do not invent enums. If an observed value does not map cleanly, use the template's unknown/manual-review enum when available.
