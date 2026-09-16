# Asteria Audit Patterns

## Universal Reconciliation

- Scope every query by the `collection_id` in `case_scope.json`.
- Use source snapshots to identify authoritative status and row counts. Prefer a `CERTIFIED` snapshot when resolving overlapping logical records. If only non-certified rows exist, retain the best available row and preserve its source basis in the code panel.
- Group duplicates by the public logical ID for the family: contact person cluster, `transaction_id`, `charge_id`, or maintenance `event_id`.
- Preserve all raw rows until duplicate, quarantine, and exception counts have been computed.
- Apply business-date cutoffs to reference validity, FX rates, source-snapshot choice, and any task-provided business period.
- Normalize strings with Unicode NFKC, trim whitespace, and casefold for comparison. Preserve display strings in the final answer when the contract requires human-readable canonical names or cities.
- For sorted arrays, sort after deduplication and before final output.

## Contact Collections

Normalize email by NFKC, trimming, and lowercasing. Normalize phones to digits only. Treat `null`, empty/whitespace strings, `N/A`, `none`, and `NULL` as unusable contact values.

Cluster contact rows only when identity evidence agrees. Same normalized email plus compatible name, same phone plus compatible name, or a non-shared master hint can support a merge. Do not merge broad shared phones or shared helpdesk-style master hints when names/emails conflict; report those as contested identifier cases when scoped.

For merged clusters, select a stable master/survivor from the most authoritative row visible in the source evidence, usually the registry/compliance/master source row when present. Canonical fields can come from different systems; assign field provenance from the row that actually supplied the winning field. HR-style sources are usually strongest for employee name/depot, while registry/compliance sources are usually strongest for contact and consent.

Readiness rules:
- A person/entity with no usable canonical email or phone is quarantined or blocked for no contact.
- Inactive records are excluded from dispatch/release even if they have contact data.
- Active records with a usable channel but non-granted consent are blocked by consent.
- Dispatchable/ready entities are active, have at least one usable canonical channel, and have granted consent. Split channel counts into both/email-only/phone-only/not-ready as the contract defines.

Contact control codes:
- `IC-70`: identity was auto-merged from compatible multi-source evidence.
- `IC-25`: single stable identity or no merge needed.
- `IC-90`: contested shared identifier evidence; do not auto-merge.
- `IC-40`: identity/contact row is quarantined because no usable contact survivor exists.
- `OR-35`: active, usable channel, consent granted.
- `OR-80`: active with usable channel but consent is not granted.
- `OR-60`: no usable outreach channel.
- `OR-15`: inactive exclusion.
- `FP-55`: canonical field chosen by field-level precedence across merged sources.
- `FP-20`: field came from a single retained source/no merge.
- `FP-75`: field provenance is quarantined or no usable field survived.

## Fuel And Freight Financial Collections

Retain one row per logical transaction/charge. For duplicate logical IDs, retain the certified/source-of-record occurrence and list all snapshot IDs in the duplicate group. Count `duplicate_raw_count` as raw rows minus logical IDs.

Reference alias matching:
- Use active, in-window aliases for the transaction or service date.
- Match alias text case-insensitively as whole words or whole phrases after punctuation normalization. Do not match alias text inside a larger word.
- Multiple aliases that map to the same canonical value count as one recognized category/class.
- Zero recognized canonical values is unrecognized; more than one distinct recognized canonical value is ambiguous.

Quarantine and mismatch rules:
- Fuel rows quarantine for nonpositive/missing quantity, unrecognized fuel alias, or ambiguous fuel aliases.
- Freight rows quarantine for nonpositive/missing billed weight, nonpositive/missing distance, unrecognized service alias, or ambiguous service aliases.
- Valid rows with recognized category/class that differs from the expected value are mismatches. They remain in normalized totals.
- Exception counts are distinct retained logical IDs that are either quarantined or valid mismatches.

Normalization:
- Convert fuel volume to the case-scope canonical volume unit with `kind=volume` conversions.
- Convert freight billed weight and distance with `kind=weight` and `kind=distance` conversions.
- Convert spend to USD with a certified FX rate for the business date. USD spends use a factor of 1.
- Sum in full precision and round only the final reported fields to the answer contract precision.

Financial decision codes:
- `RB-42`: reference row is active and valid for the business date.
- `RB-17`: reference row is inactive or outside the applicable validity window.
- `RB-83`: reference row is provisional.
- `SB-24`: retained row is a single certified/source-of-record occurrence.
- `SB-79`: retained row is a single non-certified/provisional occurrence.
- `SB-61`: duplicate logical ID where the certified/source-of-record occurrence was retained over another snapshot.
- `LD-72`: valid row; recognized category/class matches expected.
- `LD-31`: valid row; recognized category/class mismatches expected.
- `LD-14`: quarantined because no recognized alias/category/class is available.
- `LD-88`: quarantined because aliases map to multiple distinct recognized categories/classes.
- `LD-53`: quarantined because a physical measure is invalid.

Ranking patterns:
- Merchant exception rankings sort by exception count descending, then merchant ID ascending, unless the contract says otherwise.
- Carrier accrual rankings sort by normalized USD exposure from valid mismatches descending, then carrier ID ascending. Quarantined charges contribute to quarantine/exception counts but not mismatch spend.

## Maintenance Event Collections

Group duplicates by `event_id`; retained duplicate events prefer the certified snapshot. Report cross-snapshot duplicates with all snapshot IDs sorted lexicographically and the retained event/snapshot.

Reject events with missing or unparsable `event_time_raw`, invalid odometer values, negative labor, or extreme labor. If no task threshold is stated, treat clearly implausible labor values such as day-scale values as extreme while keeping normal work-order durations.

Convert odometer readings to the requested canonical distance unit before sequence checks. For each asset, sort reliable retained events by event time and stable ID. An odometer regression is a sequence-only issue: the event is not part of the invalid-event set, but it is listed in regression outputs and routed as a history exception.

Corrected distance is usually the sum across assets of the last reliable odometer reading minus the first reliable odometer reading in the reconstructed period. Exclude rejected invalid events and sequence-regression events from the reliable history unless the case scope states otherwise.

Maintenance code panels:
- `MS-12`: retained event is a single certified/source-of-record event.
- `MS-86`: retained event is a single non-certified/provisional event.
- `MS-47`: duplicate event retained from the certified/source-of-record snapshot.
- `HR-33`: accepted valid history event.
- `HR-74`: rejected invalid event.
- `HR-19`: odometer-regression history exception.

## Status Decisions

Prefer explicit maps and gates from `case_scope.json`. If a `status_action_map`, release gate, or named status/action is provided, use it exactly. Otherwise:
- `PASS`: no quarantine, mismatch, contested identity, invalid, or regression issues that affect the requested certification.
- `PASS_WITH_EXCEPTIONS`: issues exist but fall within the case thresholds.
- `HOLD`: issues exceed thresholds or an explicit gate requires blocking.
