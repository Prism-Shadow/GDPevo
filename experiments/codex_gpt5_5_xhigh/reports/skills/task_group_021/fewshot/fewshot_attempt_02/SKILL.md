# AsterOps Data-Quality Audit Skill

Use this skill for AsterOps workbench tasks that ask for a strict JSON audit answer for CRM, campaign, fleet, logistics-cost, facilities-spend, or similar data-quality loads.

## Ground Rules

- Work only from the current solver attempt directory and the remote workbench described by the task.
- Read the task prompt first, then `input/payloads/answer_template.json` if present. The template is the source of truth for output keys, controlled enum values, required empty arrays, and zero-valued buckets.
- Use the remote workbench only for environment data. Do not look for local environment source files.
- Get the base URL from the attempt's environment access file or from the task's `<TASK_ENV_BASE_URL>` substitution. The known workbench shape is:
  - Health: `<base>/api/health`
  - Catalog: `<base>/api/catalog`
  - Downloads: `<base>/downloads/<filename>`
- Query `/api/catalog` before pulling data. Use it to discover relevant API endpoints, parameters, quality-rule references, alias references, and CSV downloads for the requested batch, campaign, period, region, scope, or wave.
- Return exactly one JSON object. Do not include prose, comments, markdown fences, or extra fields.

## Recommended Workflow

1. Parse the prompt for the target slice: IDs such as batch, campaign, wave, scope, period, region, and any requested business perspective.
2. Load the answer template and preserve its top-level field order when practical.
3. Query catalog and health. Download or call only task-relevant public surfaces.
4. Load all data into a small reproducible script or notebook-like scratch calculation. Prefer structured parsing over manual counting.
5. Normalize raw fields before grouping, matching, or counting.
6. Build the effective record set, then compute totals, issue counts, review queues, samples, and decision audits from the same effective/intermediate tables.
7. Validate the final object against the template shape: all controlled enum buckets included, all requested lists present, numeric rounding applied, and no unrequested keys.

## Effective Record Rules

- Filter first by the task's target slice: period, region, scope, campaign, batch, or wave.
- Distinguish current operational API data from CSV snapshots. The API is usually the current source for totals; CSV downloads are often reconciliation evidence. Exclude CSV-only legacy, stale, or superseded snapshot rows from operational totals unless the prompt/template explicitly asks otherwise.
- Treat void, superseded, inactive, suppressed, and invalid rows as non-effective for totals, but still include them in the appropriate audit lists and issue counts.
- Amendments usually replace the superseded record. Load the amended/current record and audit both the used amendment and the excluded superseded row when fields exist for that distinction.
- Invalid rows can have multiple issue types. Count each issue type independently, even when the row is excluded from totals.
- A row can legitimately appear in more than one audit category, such as both `invalid` and `superseded`, when the data supports both labels.

## Normalization Habits

- IDs: keep as strings exactly as supplied. Sort ID lists lexicographically unless the template says otherwise.
- Email: trim whitespace and lowercase. Empty or malformed email should not make a contact reachable.
- Phone: retain digits only. Preserve leading country digits when present; do not format with punctuation.
- Domain: derive from the normalized email after `@`, lowercase.
- City and vendor names: trim; use the canonical display value from the source/reference when available.
- Descriptions and aliases: lowercase, trim, collapse repeated spaces, and compare against alias/reference tables rather than hard-coded text.
- Money: use decimal arithmetic. Convert currencies before aggregation when rates or normalized amounts are provided. Keep cents internally and emit USD amounts as JSON numbers with two decimal places where the template uses dollar fields.
- Quantities such as gallons: sum with decimal arithmetic and round final totals to two decimal places.
- Counts are integers. Empty buckets from controlled enums should be `0` or `0.00` as appropriate, not omitted.

## Deduplication and Canonical Selection

- Prefer stable business identifiers for grouping:
  - People/contact tasks: `person_key` or equivalent.
  - Campaign tasks: campaign member joined to contact person key.
  - Purchases: transaction key plus purchase ID lineage.
  - Charges/events: business key, charge/event ID, and amendment/supersession fields.
- For duplicate people or source rows, select one canonical row per person before retained/qualified counts. Apply explicit steward corrections and source precedence rules from the environment before falling back to recency or row order.
- Keep lineage audits for duplicate groups: source row IDs, selected row ID, noncanonical row IDs, and the reason such as source precedence, active correction, duplicate review, or supersession.
- Duplicate group counts are counts of groups with more than one competing row/member, not simply the number of noncanonical rows, unless the template defines a separate duplicate-row metric.
- Canonical samples should contain the canonical row after normalization, not the raw row.

## CRM and Campaign Contact Rules

- Suppression, hard blocks, bounces, opt-outs, and revoked permission override reachability. Keep these rows out of retained or qualified reachable counts even if they have email or phone.
- Reachable means there is a usable normalized email or phone after suppression/block checks.
- Contacts or members with no usable channel are dropped or routed to manual review according to the task language and template fields.
- For campaign audiences, separate hard-blocked/suppressed members from duplicate or ambiguous members that require manual review. Qualified reachable aggregates should include only actionable reachable members.
- Domain counts and segment counts should be computed only over qualified reachable members unless the prompt/template says another population.
- City retained counts should count retained contacts only, after deduplication and suppression.
- Include all segment/status enum buckets listed by the template, including zero values.

## Alias and Reference Matching

- Use the workbench's alias/reference tables for fuel classes, spend categories, units, issue types, and review reasons.
- If multiple aliases match one description, choose the alias according to reference priority/specificity. Do not let a generic substring such as a broad category term override a more specific alias.
- Record overlap, ambiguous, generic-trap, unknown, and unmapped cases in the audit fields when the template asks for them.
- Preserve controlled enum spellings from the template or reference exactly, such as fuel classes, cost types, units, categories, issue types, and review reasons.
- For expected-vs-observed checks, compare normalized canonical values, not raw descriptions.

## Fleet Fuel Audit Rules

- Canonicalize fuel descriptions through the fuel alias reference before comparing to vehicle expected fuel.
- Include effective purchases in gallon totals even when they are mismatches or documented exceptions, unless marked void/superseded/non-effective.
- Vehicle exceptions are documented separately from true mismatch-review queues.
- Zero-gallon effective purchases should remain auditable and may appear in decision fields, but they add `0.00` to totals.
- Vendor mismatch counts are grouped by vendor for true expected-fuel mismatches after exception handling.
- Source delta audits should distinguish API-only current records, CSV-only legacy records, stale CSV records, and transaction keys where API/CSV disagree.

## Logistics Cost and Facilities Spend Rules

- Build totals from effective records only: exclude void, superseded, and invalid rows from cost/spend totals.
- Convert non-USD amounts to USD using environment-provided normalized values or rates. Count non-USD issue/advisory flags independently from whether the row is effective.
- Negative amounts, missing amounts, invalid units, invalid currencies, duplicate business keys, voids, amendments, and advisory notes are separate issue types when the template lists them.
- Aggregate cost/spend by controlled type/category and include zero-valued categories.
- Top lane/vendor should be selected after all corrections, currency conversion, exclusions, and category aliasing.
- Samples should be sorted as requested, commonly by `event_id`, `charge_id`, or another stable ID, and should show adjusted/canonical values plus review reasons.

## Ordering and Output Conventions

- Preserve template key names exactly. Do not rename fields to more natural terms.
- Sort simple ID arrays ascending lexicographically unless the prompt gives a different ordering.
- Sort canonical samples by the stable identifier requested in the prompt/template, such as `charge_id`, `person_key`, `member_id`, or `event_id`.
- Sort review queues by their main entity ID and then the observed/canonical enum when multiple rows share the entity.
- For alias traces, put the selected alias/canonical decision first and list matched aliases in reference-priority or specificity order.
- For count maps based on controlled enums, use the enum order from the template. For organic maps such as domains, cities, vendors, or lanes, use stable alphabetical/key order unless the template implies ranking.
- Emit monetary and quantity fields as JSON numbers, not strings. Use two decimals for USD and gallon totals when examples/template use cents or hundredths.
- Empty arrays and zero-count maps required by the template must be present.

## Common Pitfalls

- Do not count suppressed, bounced, opted-out, or hard-blocked contacts as retained/qualified just because contact channels exist.
- Do not mix raw CSV snapshot rows into operational totals when the current API supersedes or excludes them.
- Do not drop invalid or void rows from issue counts merely because they are excluded from totals.
- Do not infer enum spellings. Copy them from the template/reference exactly.
- Do not round each component before summing. Sum with decimal precision, then round the final reported total.
- Do not omit zero buckets for controlled enums; evaluators often expect the full template shape.
- Do not use raw text for alias/category/fuel comparison when a reference table exists.
- Do not copy answer examples into future responses. Recompute from that attempt's remote data and template.
