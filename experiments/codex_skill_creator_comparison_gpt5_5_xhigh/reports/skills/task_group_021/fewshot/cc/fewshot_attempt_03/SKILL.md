---
name: asteria-hub-reconciliation
description: Use this skill for Asteria Fleet Data Quality Hub audit tasks that ask Codex to reconcile contacts, fuel transactions, freight charges, or maintenance events from task payloads, environment_access.md, and a JSON answer template. It guides schema-first hub extraction, snapshot selection, deduplication, quarantine handling, unit and FX normalization, contact readiness, maintenance history validation, ranking panels, and compact Asteria control-code decisions.
---

# Asteria Hub Reconciliation

Use this skill when a task asks for one JSON answer from the Asteria Fleet Data Quality Hub. The task will usually provide `payloads/case_scope.json`, `payloads/answer_template.json`, and `environment_access.md`.

## Ground Rules

- Read the prompt, `case_scope.json`, `answer_template.json`, and `environment_access.md` before querying the hub.
- Treat the answer template as the output contract. If it is JSON Schema, obey required keys, types, enums, precision, uniqueness, and ordering descriptions. If it is a prose field contract, treat its field descriptions as binding.
- Use only the collection, cutoff, business period, focus IDs, ranking limits, and code panels named by the task scope.
- Return exactly one JSON object. Do not include markdown, comments, or extra keys.
- Do not guess counts from samples. Fetch every page or use a complete query result.

## Fetching Data

Prefer `/api/query` when the access file supplies a working query credential. If it is unavailable, use the public REST endpoints and page with `offset` until `offset + len(items) >= total`.

Use the bundled helper to cache the public hub data for a collection:

```bash
python /path/to/skill/scripts/fetch_asteria.py \
  --access environment_access.md \
  --collection COLLECTION_ID \
  --out work/asteria_dump
```

The helper writes `catalog.json`, `schema.json`, `source_snapshots.json`, collection records, and relevant references. REST collection filters use `collection=<id>`, not `collection_id=<id>`. Alias filters use `domain=fuel` or `domain=freight`. Unit conversions require `kind=volume`, `kind=weight`, or `kind=distance`.

## Common Reconciliation Workflow

1. Select in-scope source snapshots as of the task cutoff or `as_of`.
2. Identify the authoritative snapshot basis. Prefer applicable `CERTIFIED` snapshots over `PROVISIONAL` snapshots; when a logical record appears in both, retain the certified occurrence unless the task provides a different rule.
3. Count raw rows before logical deduplication. Count logical records after grouping by the stable public ID for the family: contact row clusters, fuel `transaction_id`, freight `charge_id`, or maintenance `event_id`.
4. Build duplicate groups from logical IDs with multiple raw occurrences. Sort groups by the logical ID and sort snapshot ID lists lexicographically.
5. Validate and quarantine retained logical records before computing normalized totals. Quarantined records remain in exception and decision panels when requested, but do not enter normalized totals.
6. Compute ordered lists exactly as specified: lexicographic ID order, enum order, rank order, or the sort keys in `case_scope.json`.
7. Fill status/action fields from the task threshold or gate rules. Any hold gate or unreconciled quarantine condition generally maps to the blocking action named in the scope or template.

## Contacts And Rosters

Normalize contacts before resolving identity:

- Email: trim, Unicode-normalize if possible, lowercase, and reject blank or placeholder tokens such as `n/a`, `none`, and `null`.
- Phone: keep digits only and reject empty or placeholder values.
- Name and city: trim whitespace and preserve meaningful Unicode in the final answer.
- Active readiness: an entity is eligible only when active and it has at least one usable email or phone. A channel is ready only when consent is `GRANTED`.

Resolve definite duplicates using corroborating stable hints, normalized email or phone, source record patterns, and repeated multi-source evidence. Do not auto-merge merely because a shared helpdesk phone, shared `master_hint`, or no-contact placeholder appears across different people; those are contested or quarantine evidence.

For field-level canonicalization, do not assume one survivor supplies every field. The examples show field-specific source precedence: HR-like systems may supply canonical name and depot, registry/compliance systems may supply contact and consent, and compliance/registry rows often provide the stable master or survivor. Record the source system for each canonical field when the template asks.

For roster readiness, partition each canonical person into exactly one depot bucket: dispatchable, blocked by consent, blocked by no usable contact, or blocked by inactive status. For partner contact readiness, report mutually exclusive channel partitions: both, email only, phone only, or not ready.

## Fuel And Freight Ledgers

Use reference aliases, unit conversions, and FX rates that are effective on the business date:

- Alias recognition is unique-match based. A retained record is recognized only when its description maps to exactly one active/effective canonical fuel type or service class. Zero matches and multiple matches are unrecognized or ambiguous quarantine cases as the template names them.
- Valid class/category mismatches are exceptions but stay in normalized totals. Quarantined records are exceptions and are excluded from normalized totals.
- Physical measures must be positive and have an effective conversion to the canonical unit. Fuel quantity, freight weight, and freight distance failures quarantine the record.
- Choose certified FX rows for the transaction or service date when available. Multiply source amount by `usd_per_unit`; sum unrounded values and round only for the output precision.
- For merchant or carrier rankings, count distinct retained logical records. Apply the exact ranking metric and tie-breaks from the prompt or case scope.

Observed reusable compact-code heuristics for ledger panels:

- Reference policy: active/effective aliases use `RB-42`; inactive or not-yet-effective aliases use `RB-17`; provisional aliases use `RB-83`.
- Source basis: single certified retained rows use `SB-24`; retained rows from cross-snapshot overlap use `SB-61`; retained provisional-only rows use `SB-79`.
- Ledger routing: ordinary valid rows use `LD-72`; valid expected-vs-recognized mismatches use `LD-31`; invalid physical measures use `LD-53`; unresolved zero-match aliases use `LD-14`; ambiguous aliases use `LD-88`.

Confirm each code against the row's actual evidence before using it.

## Maintenance Events

Maintenance collections can exceed one page. Fetch every page, then:

- Group duplicate raw rows by `event_id` and retain the authoritative occurrence.
- Reject missing or unparsable timestamps, invalid odometer values, negative labor, and extreme labor as invalid events. Report those IDs in the invalid list when requested.
- Convert odometer values to kilometers using distance conversions.
- Build corrected per-asset histories from retained, non-invalid events in the business period. Sort by parsed event time and stable ID.
- Detect odometer regressions as sequence issues in otherwise parseable history. Report regression asset IDs and event IDs separately from invalid events when the template distinguishes them.
- Compute corrected distance as the sum across assets of last reliable odometer minus first reliable odometer, rounded to the declared precision.
- Rank risky assets with the sort keys from `case_scope.json`, usually rejected event count, regression event count, then asset ID.

Observed reusable compact-code heuristics for maintenance panels:

- Maintenance source codes distinguish retained certified singletons, retained certified overlap records, and retained provisional records. Derive the exact code from the scoped row's retained snapshot status and duplicate context.
- History route `HR-33` applies to valid retained history, `HR-74` to rejected invalid events, and `HR-19` to sequence-only odometer regressions.

## Contact Control Codes

When the template asks for identity, outreach, or field-provenance codes, use the row evidence rather than the label text alone.

- `OR-35`: active, usable contact channel, and granted consent.
- `OR-80`: active usable contact blocked by non-granted consent or not-ready outreach state.
- `OR-60`: no usable contact channel or quarantine-contact result.
- `OR-15`: inactive exclusion.
- `FP-55`: field-level source precedence applied across a merged multi-source cluster.
- `FP-20`: single-source or non-conflicting retained field provenance.
- `FP-75`: field provenance for quarantined/no-usable-contact evidence.
- `IC-70`: definite same-person merge.
- `IC-25`: contested shared identifier that should not auto-merge.
- `IC-40`: single no-contact quarantine identity.
- `IC-90`: unresolved repeated/no-contact or high-risk identity cluster.

These mappings are opaque policy controls inferred from examples. Use them as decision rules, not as values to paste mechanically.

## Final Checks

- Validate that all required arrays have the exact requested length when the template fixes it.
- Recompute partition sums: readiness buckets should sum to the depot or eligible total; valid plus quarantine should align with logical counts where the contract implies it.
- Sort every list after deduplication.
- Check numeric rounding at the field level requested by the template.
- Load the final JSON with a parser before returning it.
