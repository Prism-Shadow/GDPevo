# Pre-submission checklist

Work backward from `answer_template.json`; verify every item before returning.

## Scope & population
- [ ] Queried only the case-scope `collection_id`; scoped by the stated cutoff (business time,
      not ingestion time).
- [ ] Identified the authoritative CERTIFIED snapshot; used its id / row_count where asked.
- [ ] `raw_row_count` counts every in-scope source row across snapshots (no page truncation:
      cross-checked with a server-side `COUNT`).

## Reconciliation
- [ ] Right dedup shape: cross-snapshot stable-id (fuel/freight/maintenance) vs email-identity
      resolution (contacts). `logical/duplicate` or `merged_cluster` counts consistent.
- [ ] No false merges on shared phone (SHARED-HELPDESK) or common name; contested identifiers
      flagged, not merged.
- [ ] Quarantined records **included** in canonical/person counts and rollups; **excluded**
      from normalized totals.

## Canonical fields (contacts)
- [ ] Master/survivor = master_hint-bearing certified source.
- [ ] Each field resolved from its own source; `*_source_system` matches the value's origin.
- [ ] name Title-Cased & accent-preserved; email NFKC-lower-trim; phone digits only.

## Normalization
- [ ] Aliases filtered to ACTIVE ∧ in-window for the row's date; word-boundary + maximal-span
      matching; recognized/unrecognized/ambiguous split correct.
- [ ] Unit conversions applied (factor → canonical unit); FX = CERTIFIED rate on the row's date;
      USD = 1.0.
- [ ] Valid mismatches counted and included in totals under the recognized category.

## Counts, rollups, rankings, status
- [ ] Partitioned counts sum (readiness buckets = total; quarantine reasons = quarantine count;
      per-class charge counts = valid count).
- [ ] Rollups emit exactly the contract's enum members in order and sum to the population.
- [ ] Rankings apply the case_scope sort + tie-breaks exactly; limited to the requested length.
- [ ] Status/action from case_scope thresholds/gate + action map (or inferred rule), applied
      strictly.
- [ ] Opaque codes assigned by consistent ordinal tiers (deterministic fields prioritized).

## Output contract
- [ ] Exactly the required top-level keys; `additionalProperties:false` → no extras.
- [ ] Ordering / uniqueItems / min-maxItems / enums / integer-vs-number all satisfied.
- [ ] Rounding exactly as stated; string-typed numeric fields kept as strings.
- [ ] One JSON object only — no prose, no Markdown.
- [ ] Recompute headline numbers two ways and confirm they agree.
