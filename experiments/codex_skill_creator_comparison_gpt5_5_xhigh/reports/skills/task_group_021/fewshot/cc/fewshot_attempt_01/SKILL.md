---
name: asteria-fleet-audit
description: Audit Asteria Fleet Data Quality Hub tasks and produce strict JSON reconciliation answers for fleet contacts, field rosters, fuel or freight transactions, source snapshots, maintenance history, duplicate resolution, quarantine, mismatch reporting, normalized totals, rankings, certification gates, and opaque control-code panels. Use when a prompt references Asteria Fleet, TASK_ENV_BASE_URL, case_scope.json, answer_template.json, source snapshots, or the Hub query API.
---

# Asteria Fleet Audit

Use this skill to solve Asteria Fleet Data Quality Hub reconciliation tasks. The common failure mode is treating these as simple extraction tasks. Instead, reconstruct the authoritative business view from the Hub as of the scoped cutoff, compute every requested set and aggregate, then emit only the JSON object required by the answer contract.

## Inputs

Read these files before querying:

1. The task prompt.
2. `payloads/case_scope.json`.
3. `payloads/answer_template.json`.
4. `environment_access.md`, only for the base URL, credentials, and access rules needed to reach the running Hub.

Use the task's current payloads and Hub data as the only source of final values. Do not reuse IDs, counts, names, metrics, or final records from prior examples.

## Hub Workflow

1. Discover the collection in `/api/catalog/collections`.
2. Read `/api/catalog/schema` for field names, logical keys, source-system fields, units, timestamps, status fields, and any declared precedence.
3. Read `/api/source-snapshots` and choose the authoritative snapshot basis at or before the task cutoff. Prefer the snapshot that metadata marks certified or authoritative. If the task asks for source coverage, keep all in-scope snapshot rows for raw counts and duplicate groups before retaining a survivor.
4. Pull all relevant rows. Endpoints are often paginated; continue until there is no next page and no additional offset/page results. The bundled helper `scripts/hub_client.py` can perform generic GET pagination and query calls.
5. Use `/api/query` for full-table pulls, joins, grouping, and sanity checks when endpoint pagination is awkward. Query results are still subject to the same cutoff, snapshot, and answer-template rules.
6. Load reference data needed for normalization: aliases, conversions, FX rates, and any domain-specific reference tables named in the prompt.

Keep intermediate calculations in scratch files if helpful, but return only the final JSON object.

## Reconciliation Pattern

Build a retained logical record table first:

- Filter snapshots and records by the business cutoff or as-of timestamp in the case scope.
- Count raw rows before deduplicating.
- Deduplicate by the public logical business key, not by raw row ID, when both exist.
- For overlapping logical records, retain the row from the authoritative snapshot. Record every cross-snapshot duplicate group requested by the template, with snapshot ID lists sorted lexicographically.
- Compute `duplicate_raw_count` as raw in-scope rows minus retained logical records, unless the answer contract defines a narrower duplicate metric.
- Exclude quarantined records from normalized totals, but include valid expected-versus-actual mismatches in totals.
- Sort every list exactly as specified by `answer_template.json` or `case_scope.json`; common defaults are lexicographic stable ID order, ascending category/class, and ranking policies with explicit tie breaks.

Validate counts against set definitions. For example, a transaction exception count should be the distinct retained logical records that are mismatches or quarantined, without double-counting records that satisfy both conditions.

## Contacts And Rosters

For partner contacts and field-service rosters:

- Resolve people or partners by identity evidence across source systems. Multi-row clusters that represent one person/entity should produce all member row IDs sorted lexicographically and one stable master/survivor row.
- Apply field-level precedence per field, not whole-row precedence, when the schema or records show that different source systems own different canonical fields.
- Normalize emails by trimming, Unicode normalization if needed, and lowercasing. Normalize phones to digits only.
- Treat a usable channel as a nonempty normalized email or phone that passes obvious validity checks.
- A dispatchable or channel-ready entity is active, has at least one usable channel, and has granted consent for the relevant channel. Non-granted consent includes pending, denied, and unknown unless the current contract says otherwise.
- Partition readiness results so disposition counts sum to total canonical people/entities per depot or region.
- Quarantine contact rows or entities with no usable channel where the contract asks for quarantine. Inactive records with usable channels are inactive exclusions, not dispatchable records.
- Apply release or certification thresholds from `case_scope.json`. When no threshold is supplied, use the explicit gate in the case scope or the task's status/action mapping.

## Fuel And Freight Ledgers

For fuel purchases and freight charges:

- Resolve aliases against reference rows. Exactly one recognized category/class is usable. Zero matches are unrecognized; multiple matches are ambiguous.
- A class/category mismatch means the retained logical record has one recognized actual category/class and it differs from the expected category/class.
- Quarantine records with unresolved category/class, ambiguous category/class, invalid or nonpositive physical measures, invalid quantities, or other contract-defined data-quality blockers.
- Normalize units using `/api/reference/conversions` and normalize currency using `/api/reference/fx` as of the business date required by the task.
- Round monetary and physical totals to the precision in the answer contract, commonly 2 decimal places.
- Build category/service-class totals from valid retained records only. Valid mismatches remain in totals.
- Build merchant or carrier rankings from distinct retained logical exception records, using the task's ranking metric and tie breaks.

## Maintenance Histories

For maintenance-event collections:

- Use the event business period from `case_scope.json` in addition to the as-of snapshot cutoff.
- Reject events with missing or unparsable timestamps, invalid odometer ranges, negative labor, extreme labor, or any structural invalidity defined by schema or prompt.
- Treat odometer regressions as sequence issues in the reconstructed asset history. Report them separately from structural invalid IDs when the template says sequence-only regressions are excluded from invalid-event lists.
- Compute corrected distance by asset from reliable retained events: last reliable odometer minus first reliable odometer, then sum across assets and round to the declared precision.
- Rank assets using the policy in case scope, usually rejected-event count descending, regression-event count descending, then asset ID ascending.

## Opaque Codes

When a task asks for compact internal codes, infer them from the current Hub records and the reusable meanings in [references/code-semantics.md](references/code-semantics.md). Do not invent a code that is not allowed by the answer contract. If a record fits multiple code families, choose the family requested by that panel.

## Final JSON

- Conform exactly to `payloads/answer_template.json`, whether it is a JSON Schema or a custom field contract.
- Include every required key and no extra keys when `additionalProperties` or the custom contract forbids them.
- Preserve IDs from the public data and case scope. Do not fabricate stable IDs.
- Use integers for counts and numeric values for rounded measures. Keep ID-like numeric strings as strings.
- Before finalizing, check list lengths, uniqueness, sorting, partition sums, count relationships, status/action mappings, and numeric precision.
- Output only the JSON object. Do not include Markdown, commentary, citations, or explanation.
