# Reconciliation & audit workflow

Detail for steps 4–7 of `SKILL.md`.

## Raw → logical

1. Read every raw row across all relevant snapshots, tagged with snapshot id.
2. Group by stable logical id (transaction id / charge id / event id / contact
   cluster key).
3. For each logical id with >1 raw occurrence, keep the authoritative-snapshot
   occurrence; the others count toward `duplicate_raw_count`.
4. Apply the cutoff: drop rows whose timestamp is after the cutoff (or outside
   `business_period`).

## Counts

- `raw_row_count` = in-scope raw rows.
- logical count = distinct logical ids.
- `duplicate_raw_count` = raw − logical.
- valid count = logical − quarantined.

(When the contract names these differently, use its names; the relationships
above hold unless a task's narrative states otherwise.)

## Issue classification (match to the contract's buckets)

- **Mismatch**: a valid logical record whose recognized canonical category /
  service class differs from the expected class stated on the record.
  Mismatches remain valid — they enter normalized totals and feed rankings.
- **Unrecognized**: description resolves to zero canonical aliases.
- **Ambiguous**: description resolves to >1 canonical alias.
- **Invalid quantity**: nonpositive volume/weight/distance, invalid odometer
  range, missing or unparsable timestamp, negative or extreme labor.
- **Odometer regression**: a later event shows a lower odometer than an
  earlier one for the same asset. When the contract distinguishes them,
  sequence-only regressions are reported in corrected metrics, not in the
  rejected-event list.

Quarantine every logical record that is unrecognized, ambiguous, or has an
invalid quantity. Quarantined records never enter normalized totals. Count
quarantine reasons by the buckets the contract exposes (e.g. ambiguous_alias,
invalid_distance, invalid_weight, unrecognized_alias).

## Normalization

- Convert each quantity to the canonical unit from `case_scope.json` using
  `/api/reference/conversions`.
- Convert each monetary amount to the base currency using `/api/reference/fx`.
- Sum per canonical category / service class and overall; round each total to
  the precision in the answer_template (typically 2 dp).

## Canonical entity resolution (contact / people)

- Merge rows that represent the same person (duplicate clusters).
- Survivor / master id: the stable public row id retained as the entity's id
  (commonly the highest row id in the cluster).
- Canonical fields: pick each field from its authoritative source system by
  field-level precedence — infer precedence from the evidence (e.g. city from
  the compliance source, name from HR Directory, email/phone/consent from the
  identity registry). Normalize email to trimmed NFKC lowercase; phone to
  digits only; preserve Unicode in names.
- Readiness: eligible = active AND ≥1 usable email/phone; a ready channel
  requires consent `GRANTED`.
- Resolution outcomes (e.g. field-level-precedence-applied, single-source,
  contested-no-automerge, no-usable-contact) are assigned per the evidence;
  do not assume an outcome — derive it from how the cluster's sources agree
  or disagree.
