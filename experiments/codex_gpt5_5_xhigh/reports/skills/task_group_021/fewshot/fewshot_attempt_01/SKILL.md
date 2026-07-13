---
name: task-group-021-asterops-audits
description: Solve task_group_021 AsterOps data-quality audit tasks that use a remote workbench plus an answer_template JSON. Use for CRM contact/campaign reconciliation, fleet fuel audits, logistics cost integrity, facilities spend cleanup, effective-record selection, alias/reference normalization, source-vs-CSV reconciliation, and strict JSON output formatting.
---

# Task Group 021 AsterOps Audits

## Ground Rules

Work only inside the current solver attempt directory. Read the task prompt, `input/payloads/answer_template.json`, and `environment_access.md`. Do not inspect evaluator files, notes, local environment source, previous answers, or files outside the attempt directory.

Use the remote AsterOps workbench, not local source code. Read `GDPEVO_ENV_BASE_URL` from `environment_access.md`; treat `<TASK_ENV_BASE_URL>` in prompts as that value. Start with:

```bash
curl -fsS "$BASE/api/health"
curl -fsS "$BASE/api/catalog" | jq .
```

Use the catalog to discover APIs, query parameters, reference endpoints, and download filenames. Download only task-relevant CSV snapshots exposed by the catalog, usually from `/downloads/<filename>`.

## Standard Workflow

1. Read the prompt and template before fetching data. Extract the target slice: batch, campaign, region, period, wave, scope, or equivalent.
2. Convert the template into a checklist: required top-level key order, nested key order, enum values, required zero-valued keys, ordering rules, and numeric precision.
3. Fetch the current API records, reference data, quality rules, and any CSV export snapshot named in the catalog for the target slice.
4. Build normalized working tables. Keep raw IDs unchanged; add normalized helper fields for matching, contactability, aliases, currencies, and effective-record status.
5. Decide the effective record set before aggregating. Keep separate audit lists for excluded, invalid, superseded, amended, suppressed, exception, and source-delta records.
6. Populate every required output field from the effective set and audit lists. Validate counts against list lengths and group counts before writing the final JSON.

## Effective Record Rules

Prefer explicit workbench fields over inference. Common patterns:

- Exclude void records from operational totals, but report them in void/superseded audit fields when requested.
- Use amendment records as the current effective version when a record amends or supersedes an earlier record. The replaced record is superseded and should not contribute to totals.
- Exclude invalid records from spend/cost/fuel totals when the template defines invalid values as integrity exclusions. Still count and list their issue types.
- For API-vs-CSV reconciliation, current API records drive operational totals. CSV-only legacy or stale rows are usually excluded from totals and reported under source-delta or snapshot-review fields.
- Duplicate counts are by the business key named by the task, not by row count. Also count duplicate source rows when the template asks for rows beyond the first row in duplicate groups.

## CRM Contact And Campaign Rules

Normalize contact fields consistently:

- Email: trim outer whitespace and lowercase. Use `""` when no canonical email is available.
- Phone: strip all non-digits and preserve country-code digits already present. Use `""` when no canonical phone is available.
- Domain: take the lowercase domain from the retained canonical email after trimming.

Reachability means a usable normalized email or phone remains, unless the row or member is blocked by suppression, revoked consent, unsubscribe, bounce, do-not-contact, or another hard-block flag from the environment. Keep hard-blocked/suppressed rows separate from manual-review rows.

For duplicate people, group by `person_key`. Select the canonical row by explicit steward/override data first, then by source precedence from reference rules, then by recency only if no higher-precedence rule applies. Record precedence overrides when the selected row differs from the newest row because of source precedence.

Counts and samples usually include unique canonical people, not raw rows. City, domain, and segment counts include retained qualified/reachable canonical people only. Include all required segment enum keys with `0` when absent. Sort canonical contact/member samples by `person_key` unless the template says otherwise.

## Alias And Reference Resolution

Use remote reference endpoints for controlled aliases and quality rules. Do not hardcode aliases from prior tasks.

Normalize descriptions for matching with case-insensitive, trimmed comparisons. When multiple aliases match, select by the reference priority or specificity rule exposed by the environment. Preserve the selected alias text and matched alias list when the template asks for an alias trace.

Common audit distinctions:

- `priority_overlap`: more than one alias matches and priority decides the canonical class.
- Generic trap cases: a generic alias also matches a more specific alias; count and trace these separately when requested.
- Unknown alias: the selected alias maps to an `unknown` class.
- Unmapped description: no alias matches.
- Ambiguous category: multiple category aliases remain unresolved after the reference rules.

Use enum values exactly from the template for fuel classes, categories, review reasons, cost types, units, issue types, source actions, and operations actions.

## Fuel Audit Rules

For fleet fuel tasks, determine canonical fuel from the alias reference before comparing against vehicle expected fuel. Effective purchase records contribute to gallons by canonical fuel, including zero-gallon records as zero.

Mismatch queues include effective purchases whose observed canonical fuel differs from the vehicle expected fuel, excluding documented vehicle/business exceptions. Exception purchases are listed separately and usually still remain in totals unless the template says otherwise.

Vendor mismatch counts are based only on mismatch purchase IDs. Vehicle review queues group by vehicle and observed fuel, with purchase IDs sorted. Source-delta fields reconcile current API purchases against the CSV snapshot by transaction key and purchase ID.

## Cost And Spend Rules

Use the quality-rule reference for currency conversion and unit validity. Convert monetary values with decimal arithmetic:

- Round each included line/event/charge converted amount to USD cents before aggregation.
- Aggregate already-rounded cents into category, cost-type, lane, vendor, and total values.
- Report USD numbers as JSON numbers with two decimal places when writing by hand; do not quote them as strings.

Invalid negative amounts, missing amounts, invalid units, and invalid currencies are integrity exclusions when the template defines them that way. Non-USD records can still be valid after conversion; count or sample them exactly as the template describes.

For top vendor or top lane, rank by adjusted/included spend after exclusions and conversions. Break ties only if the template or data rules specify one; otherwise use stable ascending names/IDs and document the choice in scratch work, not in the final JSON.

## Output Conventions

Match the answer template exactly:

- Emit one JSON object and no prose when the task asks for JSON-only output.
- Preserve required top-level key order and nested item key order from the template.
- Include all required object keys, especially enum buckets with zero counts or `0.00` totals.
- Sort ID lists ascending lexicographically unless the template names a different ordering.
- Sort samples and audit arrays by the template key, commonly `person_key`, `purchase_id`, `event_id`, `charge_id`, or `transaction_key`.
- Sort issue/review-reason lists by template enum order when specified; otherwise use ascending enum label.
- For "top N" summaries, sort by metric descending, then label ascending for ties, and include only the requested number.
- Avoid extra properties unless the template explicitly allows them; even then, extra fields are not useful.

Before finalizing, run a JSON parse check and verify:

- Counts match the lengths or grouped universes they claim to summarize.
- Suppressed, invalid, superseded, exception, and manual-review rows are not accidentally included in retained/effective totals.
- Source API and CSV snapshot rows are not double-counted.
- Currency and gallon totals use the required rounding level.
- All enum spellings come from the template or remote reference data.
