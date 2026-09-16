# Asteria Hub Reconciliation Playbook

Use this playbook after loading the task prompt, scope, answer contract, hub schema, snapshots, and source rows. The examples indicate a family of audits with the same structure: snapshot selection, duplicate collapse, domain normalization, exception reporting, ordered scoped panels, and a final release or hold decision.

## Source And Snapshot Handling

- Treat `case_scope.json` as the authority for collection ID, cutoff/as-of time, focus IDs, ranking limits, scoped decision IDs, thresholds, and sort policies.
- Use catalog and schema endpoints to identify record fields before writing queries. Source endpoints may be paginated; keep fetching until no cursor, next URL, or additional page remains.
- Include only rows in the scoped collection and business period/cutoff requested by the task.
- Determine the authoritative snapshot from snapshot metadata as of the cutoff. Certified snapshots outrank provisional snapshots when both cover the same logical row.
- Collapse duplicates by the stable logical ID used by the domain: transaction ID, charge ID, event ID/logical event ID, person/contact cluster, or the domain's explicit cluster key.
- For duplicate reporting, list all source snapshot IDs containing the logical record in lexicographic order and identify the retained authoritative occurrence.

## Contacts And Rosters

- Normalize emails with trimming, Unicode normalization if the task asks for it, and lowercase comparison. Normalize phone values to digits only.
- A usable contact channel is a nonempty normalized email or phone that passes the record's validity flags. No usable channel is a quarantine or no-contact block, depending on the answer contract.
- Resolve people or partner contacts by identity evidence first, then choose field-level canonical values using source precedence visible in schema/source metadata. Do not assume one row supplies every canonical field.
- For readiness partitions, count canonical people/entities once. A dispatchable or ready person is active, has at least one usable channel, and has granted consent. Non-granted consent with a usable channel is a consent block. Inactive people with usable channels are inactive blocks. No usable channel is a no-contact block.
- For focus clusters, return every member row ID sorted lexicographically, the retained/master row ID, canonical contact fields, source systems for canonical fields, and the stated resolution outcome.
- For watchlists, report only identifier cases that remain contested after applying the automerge rules and source evidence.

## Fuel And Freight Ledgers

- Resolve aliases through `/api/reference/aliases`; use conversions and FX endpoints to normalize units and spend to the case-scope canonical units and base currency.
- Separate three concepts: raw rows, logical transactions/charges after duplicate collapse, and valid records that enter normalized totals.
- Category or service-class mismatches are valid records whose recognized class differs from the expected class. Keep them in normalized totals unless the prompt says otherwise.
- Quarantine records whose class/category is unresolved, ambiguous, or whose physical quantity is invalid. Exclude quarantined records from normalized volume, weight, distance, and spend totals.
- Count unrecognized and ambiguous alias/category cases separately when the contract asks, but include both in the combined unresolved ID list if the contract defines it that way.
- Merchant or carrier exception rankings use distinct retained logical records. Apply the prompt's exact sort policy, typically exception count or mismatch exposure descending with stable ID ascending as the tie break.

## Maintenance Histories

- Reject events with missing or unparsable timestamps, invalid odometer ranges, or invalid labor ranges. Report these rejected public event IDs sorted as required.
- Do not treat odometer sequence regressions as rejected events unless the prompt says so. Detect regressions after reconstructing each asset's valid event history in timestamp order.
- Corrected distance is the sum across assets of the last reliable odometer reading minus the first reliable odometer reading in the reconstructed period, rounded to the requested precision.
- Risk rankings combine rejected event counts and regression counts by asset. Use the primary sort and tie breaks in case scope exactly.
- If the certification gate maps any odometer regression to hold, use that status/action mapping rather than inventing a separate policy.

## Reusable Control-Code Rules

The opaque codes are stable decision labels inferred from the public evidence and prior answer contracts. Assign them from the current task's rows and audit state, never from a row ID pattern alone.

| Family | Code | Use when current evidence shows |
| --- | --- | --- |
| Field provenance | FP-20 | Single-source or direct-retained field evidence without field-level merging. |
| Field provenance | FP-55 | Field-level precedence was applied across multiple source rows/systems. |
| Field provenance | FP-75 | Field evidence is unusable or the row/entity is quarantined. |
| Identity | IC-25 | A single source identity is retained without merging. |
| Identity | IC-40 | Identity/contact evidence is unusable enough to quarantine or exclude. |
| Identity | IC-70 | Multiple rows resolve to the same canonical identity. |
| Identity | IC-90 | Identifier evidence remains contested and cannot be automerged. |
| Outreach | OR-15 | Inactive record exclusion. |
| Outreach | OR-35 | Ready or dispatchable: active, usable channel, consent granted. |
| Outreach | OR-60 | No usable outreach channel or outreach quarantine. |
| Outreach | OR-80 | Usable channel exists but consent/status prevents readiness. |
| Reference rows | RB-42 | Alias/reference maps cleanly to one recognized canonical class. |
| Reference rows | RB-17 | Alias/reference is ambiguous across recognized classes. |
| Reference rows | RB-83 | Alias/reference is unrecognized. |
| Source basis | SB-24 | Single retained source occurrence. |
| Source basis | SB-61 | Certified/authoritative occurrence retained from duplicates. |
| Source basis | SB-79 | Non-authoritative or alternate source basis is the relevant evidence state. |
| Ledger route | LD-72 | Valid, recognized, and aligned with expected class/category. |
| Ledger route | LD-31 | Valid class/category mismatch. |
| Ledger route | LD-14 | Unrecognized class/category quarantine. |
| Ledger route | LD-88 | Ambiguous class/category quarantine. |
| Ledger route | LD-53 | Invalid physical quantity or measure quarantine. |
| Maintenance source | MS-47 | Certified/authoritative maintenance source basis. |
| Maintenance source | MS-12 | Single-source maintenance basis. |
| Maintenance source | MS-86 | Alternate/provisional maintenance source basis. |
| History route | HR-33 | Valid event retained in corrected history. |
| History route | HR-19 | Valid event retained but flagged for odometer regression. |
| History route | HR-74 | Event rejected from corrected history. |

When a scoped decision panel includes codes but the hub also exposes explicit policy/code fields, prefer the hub's explicit stable code over these inferred rules. Otherwise, use the rules above and verify each code against the record's source, duplicate, alias, quarantine, mismatch, consent, or history state.

## Output Discipline

- Build the answer object directly from the template keys. Do not include explanatory fields, Markdown, or provenance notes unless the contract includes them.
- Preserve stable IDs exactly as supplied by the hub or case scope.
- Sort every array according to the contract, not according to query return order.
- Round only at output boundaries. Keep intermediate calculations at full precision.
- For final status/action, apply the task's thresholds or status-action map exactly. If no threshold is supplied, use the prompt's named gate or the contract's decision semantics.
