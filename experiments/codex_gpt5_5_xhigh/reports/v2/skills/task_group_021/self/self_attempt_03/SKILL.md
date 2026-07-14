---
name: asterops-data-quality-audits
description: Solve AsterOps remote-workbench data quality audit tasks by deriving effective records, applying reference rules, reconciling exports, and emitting exact template JSON.
---

# AsterOps Data Quality Audits

Use this skill for AsterOps audit tasks that provide a prompt, `input/payloads/answer_template.json`, and `environment_access.md` pointing at a remote workbench.

## Material Boundaries

- Work only inside the current solver attempt directory.
- Read only the task prompt, answer template, `environment_access.md`, and input payloads provided for the attempt.
- Do not read environment source, tests, evaluator files, notes, prior answers, or paths outside the attempt directory.
- Use the remote AsterOps workbench from `environment_access.md`; do not infer data from local files.

## Standard Workflow

1. Read the prompt and the answer template before touching the API.
2. Extract the base URL from `environment_access.md`; check `/api/health`, then read `/api/catalog`.
3. From the catalog, identify the relevant endpoints, filters, field names, and downloads.
4. Pull the target API slice using the prompt's identifiers such as campaign, batch, wave, region, period, or scope.
5. Pull reference endpoints named by the prompt, especially quality rules and alias maps.
6. Pull cataloged CSV downloads when the prompt mentions shared downloads, export snapshots, source reconciliation, or source deltas.
7. Treat `answer_template.json` as the output contract: key order, required enum keys, item fields, sorting, and precision override general instincts.
8. Build a local audit table with normalized fields, effective-record decisions, review reasons, and evidence lists before aggregating.
9. Emit exactly one JSON object and no prose for answer tasks.

Useful API pattern:

```bash
BASE="$(awk -F= '/GDPEVO_ENV_BASE_URL/ {print $2}' environment_access.md)"
curl -sS "$BASE/api/catalog"
curl -sS "$BASE/api/reference/quality_rules"
```

## Output Conventions

- Preserve required top-level key order when the template specifies it.
- Preserve nested item key order for sample/audit rows when specified.
- Use controlled enum values exactly as written in the template or reference data.
- Include all required enum/object keys even when the value is `0`, `0.00`, `[]`, or `{}`.
- Sort ID lists lexicographically unless the template gives a different rule. Do not numeric-sort ID suffixes.
- Sort evidence rows by the template's primary key, usually an ID, `person_key`, `business_key`, `lane`, or transaction key.
- For dynamic count objects, follow the template rule. Common patterns are count descending then name ascending, or include only positive-count keys.
- Use integers for counts.
- Use JSON numbers, not strings, for money and gallons. Internally use `Decimal`; for currency render to cents and for gallons render to two decimals when required.
- When a template says additional properties are false, include no extras. Even when extras are allowed, avoid them unless needed for a required field.

## Shared Business Rules

### Effective Records

- `record_status: "void"` rows are non-effective and excluded from operational totals.
- `record_status: "amended"` rows are effective replacement rows unless they are independently invalid.
- Any row whose ID is referenced by an `amends_*` field is superseded and excluded from totals.
- Keep void, amended, and superseded evidence in separate lists when the template asks for them.
- Do not classify an ordinary void or superseded row as invalid unless it also fails an explicit validity rule.
- For duplicate `business_key` or `person_key` groups, distinguish group counts from row counts:
  - duplicate group count = number of keys with more than one row.
  - duplicate row count = rows beyond the first within duplicate groups, if requested.
- If the API and CSV disagree, use the current API records for operational totals unless the prompt says otherwise; use CSV rows for reconciliation evidence.
- CSV-only legacy rows and stale CSV rows should usually be excluded from operational totals but listed in source-delta audit fields.

### Invalid Data

Common invalid conditions:

- missing or non-numeric required amount.
- negative amount where costs/spend must be nonnegative.
- invalid currency not present in the quality-rule conversion table.
- invalid unit not present in the quality-rule controlled unit list.
- unmapped or unknown aliases when the template treats them as review issues.

Use issue/review reason enums from the template. For issue lists, use the template's enum order when it says "template enum order"; use lexical label order only when the template explicitly says so.

## CRM Contacts And Campaigns

Normalize CRM channels before decisions:

- Email: trim outer whitespace and lowercase.
- Phone: remove every non-digit character; preserve country-code digits.
- A row/person is reachable if normalized email or normalized phone is nonempty.
- Use an empty string, not `null`, when the template wants a missing canonical email or phone.

Suppression and contactability:

- Source rows with `contact_status: "do_not_contact"` or `consent_status: "revoked"` are suppressed.
- Suppressed rows with usable channels remain suppressed; list them in suppression evidence if requested.
- `contact_status: "inactive"` or stale notes are not loadable if a better active candidate exists; track them in stale/inactive counts when requested.
- A canonical person with no usable normalized channel is dropped as unreachable, not retained.
- A person with only suppressed candidates is suppressed/blocked, not counted as reachable.

Canonical contact selection:

- First remove suppressed rows from canonical candidates, while preserving them for evidence.
- Prefer active stewardship corrections when present.
- Otherwise use source precedence: `steward_override`, `crm_verified`, `partner_roster`, `event_import`.
- Use source update date and then row ID as deterministic tie-breakers.
- For duplicate-person lineage, include all source row IDs for the person, the selected row ID, noncanonical row IDs, and a decision reason from the template.

CRM import aggregates:

- Count retained contacts from retained canonical people only.
- Count dropped unreachable canonical people separately.
- City/domain/segment counts are based only on retained reachable canonical people.
- Top-N city objects usually sort by count descending, then city name ascending.
- Normalization-change counts are row-based: count nonblank email/phone values that change under the required normalization.

Campaign audience tasks:

- Reconcile campaign members to canonical CRM contacts by `person_key`.
- Hard-block campaign member statuses such as `bounced` and `unsubscribed`.
- Keep hard-blocked/suppressed members separate from members needing manual review.
- Duplicate campaign member rows for the same `person_key` require a canonical member decision; noncanonical duplicates generally go to duplicate/manual-review evidence.
- Prefer actionable member statuses, then higher score, then deterministic member ID ordering unless the prompt gives a stronger rule.
- Segment normalization should be case-insensitive and trim whitespace; map known words to template segment enums and default to `unknown`.
- Domain counts use the retained canonical email domain after trimming and lowercasing.

## Alias Resolution

Alias references use case-insensitive substring matching against the relevant raw description/category field.

General alias procedure:

1. Lowercase and trim the source text.
2. Find all aliases whose alias text appears in the source text.
3. Select the highest `priority`; use alias text as a stable tie-breaker.
4. Use the selected alias's canonical value for aggregation.
5. If no alias matches, use the template's unknown/unmapped handling.
6. If multiple aliases match, record the priority/ambiguity evidence requested by the template.

Fleet-specific alias notes:

- Fuel descriptions can match both a generic alias and a more specific alias.
- The generic `unleaded` match is a trap when a specific unleaded alias also matches; select the specific higher-priority alias and record the trap if requested.
- Selected aliases mapping to `unknown` are distinct from descriptions with no alias match.

Facilities-specific alias notes:

- Use the category alias reference for charge categories.
- Prefer `raw_category` for category matching unless the prompt or schema directs otherwise.
- Multiple category aliases on one charge can be an ambiguous-alias review reason even when the highest-priority alias is selected.

## Fleet Fuel Audits

- Filter purchase records by prompt region and period.
- Fetch vehicles for the region and join by `vehicle_id`.
- Build effective purchases after void/amendment/superseded handling.
- Resolve observed fuel from alias priority.
- Compare observed fuel to the vehicle's expected fuel.
- Purchases with mismatched fuel and no vehicle exception enter the mismatch queue.
- Purchases with mismatched fuel and a non-`none` vehicle `exemption_code` are business exceptions, not mismatches.
- Zero-gallon purchases remain effective if not otherwise invalid; list them separately when requested.
- Gallon totals are by selected canonical fuel over effective purchases and rounded to two decimals.
- Vendor mismatch counts include only vendors with at least one non-exception mismatch.
- Reconcile API purchases to CSV export rows by purchase ID and transaction key when requested:
  - API-only current records are current-source evidence.
  - CSV-only rows are legacy/export evidence.
  - CSV rows replaced by current API amendments are stale or superseded evidence.
  - Transaction reconciliation rows should group all current API IDs, excluded IDs, and CSV IDs for the same transaction key.

## Logistics Cost Audits

- Filter cost events by `wave_id`.
- Use quality-rule currency rates for conversion.
- Use quality-rule unit values for unit validity.
- Exclude void, superseded, and invalid records from corrected totals.
- Valid amended events replace their referenced prior event.
- Invalid event issue lists should include all applicable invalid issue types, sorted by template enum order.
- Count issue types over the in-scope source rows according to template descriptions, not only over included totals.
- Count non-USD currency separately from invalid currency; a known non-USD currency is valid but requires conversion.
- Convert each included event amount to USD and round that line to cents before aggregation.
- Aggregate corrected total, cost-type totals, unit counts, and lane totals from included effective events only.
- For top lane/vendor summaries, select the largest adjusted spend; use stable lexical tie-breakers if needed.
- Non-USD sample lists usually mean the first N non-void source IDs with amount present, sorted ascending.

## Facilities Charge Audits

- Filter charges by prompt scope and period.
- Use API and CSV together only when the prompt asks for source conflict or export reconciliation; otherwise the API slice is the operational source.
- Build effective charges after excluding void, invalid, and superseded rows.
- Amended charges replace the charge referenced by `amends_charge_id`.
- Classify categories through category aliases and include every required category key in count and spend objects.
- Spend is adjusted spend over effective charges only, in USD cents.
- Review reason counts can include reasons on excluded rows when the template's review fields describe all source issues; do not let excluded rows contribute to spend totals.
- Canonical charge samples are sorted by `charge_id`; review reasons inside each row follow the template's ordering rule.
- Top vendor spend uses effective adjusted spend only, and its charge IDs are sorted ascending.

## Common Pitfalls

- The remote environment contains background rows. Always filter by the task identifiers from the prompt.
- The API slice alone may not satisfy source-delta fields; inspect CSV downloads when exports are mentioned.
- Do not aggregate before applying effective-record, invalid, suppression, and duplicate decisions.
- Do not let suppressed-but-reachable CRM rows count as retained audience.
- Do not count duplicate groups and duplicate rows interchangeably.
- Do not use quality notes as the only source of truth; compute invalid, normalization, alias, and suppression conditions from fields.
- Do not aggregate converted currency first and round once; round each included line to cents, then sum cents.
- Do not omit zero-valued required enum keys.
- Do not use answer examples or train IDs in a future answer; derive all values from that attempt's prompt, template, and remote workbench.
