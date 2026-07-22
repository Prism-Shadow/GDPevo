---
name: asteria-data-quality-audits
description: Reconcile Asteria Fleet Data Quality Hub collections and produce exact JSON audit/certification answers from prompts that provide a case_scope.json, answer_template.json, environment_access.md, and Asteria hub endpoints. Use for contact-master/onboarding/roster readiness, fuel ledger normalization, freight accrual cleanup, and maintenance-history integrity tasks requiring source snapshot selection, duplicate retention, quarantine decisions, normalized totals, ranking panels, and compact Asteria control codes.
---

# Asteria Data Quality Audits

Use this skill to solve Asteria Fleet Data Quality Hub audit tasks. Return exactly the requested JSON contract; do not add commentary when the prompt says JSON only.

## Inputs

1. Read the user prompt, `payloads/case_scope.json`, `payloads/answer_template.json`, and `environment_access.md`.
2. Treat the answer template as the output authority: required keys, allowed enum values, sort order, lengths, uniqueness, and precision come from the template even when the prompt is brief.
3. Use only the hub base URL and endpoints/credential in `environment_access.md`. Do not use external sources.
4. Inspect `/api/catalog/collections`, `/api/catalog/schema`, and `v_source_snapshots` before querying facts for the scoped collection.

The authenticated query interface accepts JSON like:

```bash
curl -sS -X POST "$BASE/api/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"select * from v_source_snapshots where collection_id='\''<collection_id>'\'' order by snapshot_id"}'
```

Use `limit` and `offset` when a collection can exceed one response page.

## Source Retention

1. Filter rows to the scoped `collection_id` and business cutoff or period from `case_scope.json`.
2. Use source snapshots whose `business_cutoff` is applicable to the scope. Prefer `CERTIFIED` snapshots over `PROVISIONAL` snapshots.
3. Group overlapping records by the stable logical ID:
   - contacts: resolved person cluster, not just a raw row ID.
   - fuel: `transaction_id`.
   - freight: `charge_id`.
   - maintenance: `event_id` or the contract's logical event ID.
4. Retain the certified occurrence when a logical ID appears in both certified and provisional snapshots. Keep a provisional-only occurrence only when no certified occurrence exists.
5. Count duplicates as raw occurrences minus retained logical records, or by the template's explicit duplicate definition.
6. For duplicate panels, list every logical ID with multiple raw occurrences, sort by logical ID, sort `snapshot_ids` lexicographically, and report the retained snapshot.

Use these source-code meanings when the output contract asks for compact source basis, source retention, or maintenance source codes:

| Code | Meaning |
| --- | --- |
| `SB-24` | Certified-only retained transaction or charge. |
| `SB-61` | Certified occurrence retained over an overlapping provisional duplicate. |
| `SB-79` | Provisional-only retained transaction or charge. |
| `MS-12` | Certified-only retained maintenance event. |
| `MS-47` | Certified maintenance event retained over an overlapping provisional duplicate. |
| `MS-86` | Provisional-only retained maintenance event. |

## Contact Audits

### Normalize Contact Fields

- Normalize emails with Unicode NFKC, trim whitespace, and lowercase.
- Normalize phone numbers to digits only.
- Treat empty strings, whitespace, `n/a`, `none`, `null`, and values with no digits as unusable.
- Preserve Unicode in display names; trim and normalize spacing. Convert all-caps display names to normal title casing only when doing so preserves accents and particles safely.

### Resolve People

1. Build strong merge edges from matching normalized email, matching normalized phone with compatible name or email evidence, and stable master hints that are not noisy/shared placeholders.
2. Treat hints like shared helpdesk, noisy, blank, or placeholder identifiers as weak evidence. Do not merge on them without a strong email/name/phone agreement.
3. Do not merge solely on repeated name, repeated city/region, a shared phone used by many distinct names, or no-contact rows.
4. Merge transitively after rejecting weak-only edges.
5. Mark weak identifier cases as contested when the evidence points to multiple possible people and no high-confidence automerge is justified.

### Choose Canonical Values

For each resolved person, choose non-empty canonical fields by consensus first, then by certified/verified source evidence, then by source-specific field authority, then by most recent `business_updated_at`, then by stable row ID.

Use the collection's source systems to infer field authority. In the observed Asteria contact collections:

- Operational/roster sources such as `HR Directory` or `Partner Portal` are usually best for consent, depot/region, and Unicode-preserving display names.
- Registry/master sources such as `Identity Registry` or `Compliance Master` are useful corroboration for identity and normalized contact fields.
- CRM/dispatch provisional rows are lower precedence when they conflict with certified sources.

For readiness:

- A person is dispatch/readiness eligible only when canonical status is `ACTIVE` and at least one canonical email or phone is usable.
- A channel is ready only when canonical consent is `GRANTED`.
- Count active usable-channel people with non-granted consent as not ready or blocked by consent.
- Exclude inactive people from readiness counts and report them in inactive-exclusion panels when required.
- Quarantine rows or people with no usable email and no usable phone as the contract directs.

Use these contact control-code meanings:

| Code | Meaning |
| --- | --- |
| `IC-25` | Single stable identity with no merge required. |
| `IC-40` | Deterministic same-person merge from strong identifiers or corroborated multi-source evidence. |
| `IC-70` | Contested identity; weak/shared evidence is insufficient for automerge. |
| `IC-90` | No usable identity/contact evidence for a reliable canonical person. |
| `OR-15` | Dispatchable/outreach ready: active, usable channel, consent granted. |
| `OR-35` | Active with usable channel but blocked because consent is not granted. |
| `OR-60` | Inactive exclusion with otherwise usable contact evidence. |
| `OR-80` | No usable outreach channel. |
| `FP-20` | Single-source or no-conflict field provenance. |
| `FP-55` | Field-level precedence applied across merged/conflicting source records. |
| `FP-75` | No usable canonical field evidence or quarantined field provenance. |

If a template asks for codes under channel buckets such as `both`, `email_only`, or `phone_only`, assign the ready-code (`OR-15`) to consent-granted ready buckets unless the contract explicitly defines channel-specific code values. Assign blocked consent, inactive exclusion, and no-channel cases to `OR-35`, `OR-60`, and `OR-80` respectively.

## Fuel And Freight Audits

### Reference Alias Classification

1. Load `v_reference_aliases` for the relevant domain (`fuel` or `freight`).
2. For each retained transaction/charge, use the business date (`purchased_at` date for fuel, `service_date` for freight).
3. A classification alias is usable only when:
   - `reference_status = 'ACTIVE'`.
   - `valid_from` is on or before the business date.
   - `valid_to` is null or on or after the business date.
4. Match alias text case-insensitively with word/phrase boundaries.
5. Prefer the longest non-overlapping alias spans so a specific phrase such as "premium unleaded" is not made ambiguous by the generic alias "unleaded".
6. After suppressing shorter overlapping spans, collect distinct canonical values:
   - zero values: unrecognized.
   - one value: recognized canonical category/class.
   - more than one value from non-overlapping evidence: ambiguous.

Use these reference-policy code meanings:

| Code | Meaning |
| --- | --- |
| `RB-17` | Active reference row usable for classification at the audited business date. |
| `RB-42` | Retired/inactive historical reference row; useful for policy explanation but not an active classifier. |
| `RB-83` | Provisional or not date-effective reference row; do not use for classification. |

### Quarantine And Mismatches

- Fuel quarantine conditions: no recognized fuel category, ambiguous category, or nonpositive/invalid quantity.
- Freight quarantine conditions: no recognized service class, ambiguous class, nonpositive/invalid billed weight, or nonpositive/invalid distance.
- Expected-versus-actual mismatches are not quarantined when all physical/classification data is valid. Include valid mismatches in normalized totals and mismatch rankings.
- Quarantined records do not enter normalized totals or valid-record counts.
- Exception counts are distinct retained logical records with a mismatch or quarantine condition.

Use these ledger disposition codes:

| Code | Meaning |
| --- | --- |
| `LD-14` | Valid recognized record whose expected class/category matches the recognized value. |
| `LD-31` | Valid recognized record whose expected value differs from the recognized value. |
| `LD-53` | Unrecognized alias/category/class. |
| `LD-72` | Ambiguous alias/category/class. |
| `LD-88` | Invalid physical measure, such as nonpositive quantity, weight, or distance. |

When more than one ledger issue applies, prefer the physical-measure code over alias/classification codes, because invalid physical data prevents ledger entry regardless of category.

### Normalization

- Convert fuel volume with `v_unit_conversions.kind = 'volume'`.
- Convert freight weight and distance with `kind = 'weight'` and `kind = 'distance'`.
- Convert maintenance odometer readings with `kind = 'odometer'`.
- Use certified FX rows for the record's business date and currency. Multiply amount by `usd_per_unit`; do not assume USD is exactly 1 unless the reference row says so.
- Round final totals to the precision in the answer template. Avoid rounding intermediate values except where the template requires it.
- Sort totals and ID arrays exactly as the template states.

For merchant exception rankings, sort by exception count descending, then merchant ID ascending. For freight carrier exposure rankings, sort by normalized USD exposure from valid mismatches descending, then carrier ID ascending; quarantined charges do not add mismatch exposure.

## Maintenance Audits

1. Retain one occurrence per event using the source-retention rules.
2. Restrict events to the scoped business period after parsing the event timestamp.
3. Hard-reject retained events for:
   - missing timestamp.
   - unparsable timestamp.
   - nonpositive or invalid odometer after unit conversion.
   - negative labor hours.
   - extreme labor sentinel values; Asteria maintenance ledgers use `120.0` hours as an extreme invalid value.
4. Count issue categories on retained logical events unless the template explicitly asks for raw-row counts.
5. Sort retained, hard-valid events by `asset_id`, parsed event time, and event ID. Convert odometer values to kilometers before sequence checks.
6. Mark an odometer regression when an event's odometer is below the prior reliable odometer for that asset. Report regressions separately from hard rejects.
7. Build corrected distance by asset as last reliable odometer minus first reliable odometer after excluding hard rejects and sequence-regression readings.
8. Risk rankings use hard rejected event counts plus regression counts according to the case-scope sort policy.

Use these maintenance history-route codes:

| Code | Meaning |
| --- | --- |
| `HR-19` | Accepted reliable event in reconstructed history. |
| `HR-33` | Sequence-only odometer regression. |
| `HR-74` | Hard rejected event. |

If the case scope declares a certification gate for odometer regression, apply its status/action whenever any regression remains. Otherwise map no exceptions to `PASS`/`RELEASE`, remediable exceptions to `PASS_WITH_EXCEPTIONS`/`REVIEW_EXCEPTIONS`, and blocking data-quality failures to `HOLD`/`BLOCK_AND_REMEDIATE` according to the prompt or scope thresholds.

## Output Discipline

1. Construct the final object directly from `answer_template.json`; do not include unspecified keys.
2. Use stable public IDs from the hub or case scope only.
3. Deduplicate arrays before sorting.
4. Preserve required ordering:
   - lexicographic ID order for scoped panels unless another ranking is specified.
   - rank order for ranked arrays.
   - enum/category ascending where the template says one row per category/class.
5. Recompute count partitions from the same retained canonical set used for detail panels.
6. Validate JSON syntax and, when practical, validate against the JSON Schema or custom contract before answering.
7. Do not include training-task final counts, IDs, or solved outputs in reusable skill instructions.
