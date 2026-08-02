# Hub query & triage recipes (reusable)

Generic patterns for pulling and triaging a matter's records. Send SQL to the hub's
read-only query endpoint using the base URL and credential header from the run's
environment access file. Replace `:matter` with the task's matter id. No values here
are matter-specific — recompute everything per matter.

## 1. Orient

```sql
SELECT * FROM matters WHERE matter_id = ':matter';                 -- name, hold_date
SELECT category_code, title FROM subpoena_categories
  WHERE matter_id = ':matter' ORDER BY category_code;              -- this matter's code scheme
```

## 2. Backbone first — the material target set

```sql
SELECT action_id, target_ref, action_type, priority, severity, owner, due_days
FROM remediation_actions
WHERE matter_id = ':matter' AND action_id NOT LIKE '%NOISE%';
```

Every `target_ref` here is a material record. Look each up in its table by ID prefix
(`SRC-…` custodian_sources, `PRIV-…` privilege_entries, `QC-…` qc_findings,
`RET-…` retention_events, `DOC-…` review_documents).

## 3. Pull each signal table, then keep only material (descriptive-ID) rows

```sql
SELECT * FROM custodian_sources WHERE matter_id = ':matter';
SELECT * FROM privilege_entries WHERE matter_id = ':matter';
SELECT * FROM qc_findings       WHERE matter_id = ':matter';
SELECT * FROM retention_events  WHERE matter_id = ':matter';
SELECT category_code, status, produced_count, responsive_count, withheld_count,
       zero_claim_reason
FROM production_stats
WHERE matter_id = ':matter'
  AND (zero_claim_reason <> '' OR produced_count = 0);   -- zero-production claims
```

**Keep** rows whose ID is descriptive (`<TYPE>-<MATTER>-<DESCRIPTOR>`) and whose note
states a concrete defect. **Drop** numbered rows (`<TYPE>-<MATTER>NN`) and rows whose
note is boilerplate ("operational noise", "ordinary review variance", "similar labels
across matters", "requires category-level context before escalation", "no
production-impacting issue has been escalated yet", "follow-up but not immediate
remediation", "remediated by archive collection", "minor metadata normalization").
The kept set must equal the backbone `target_ref` set.

## 4. Metric building blocks

- Pre/post-hold split: compare each retention event's `event_date` to `matters.hold_date`
  (or read `status` = `policy_destroyed_pre_hold` vs. `post_hold_loss`).
- Box counts: `SUM(volume_count)` over material retention events with a boxes `volume_unit`.
- Unlogged privilege: `withheld_count - logged_count` for `incomplete_log` entries.
- Waiver docs: withheld of `third_party_waiver` entries.
- Responsiveness miscodes: `doc_count` of material `miscoded_nonresponsive` /
  `zero_claim_contradiction` findings.
- Personal-source gaps: material `custodian_sources` with a personal `source_type`
  and a not-collected/partial/lost `status`.
- Affected categories: union of `category_impacts` / `affected_categories` /
  `affected_category` across material records → count, and the list sorted ascending
  and upper-cased.
- Any open material gap ⇒ the readiness/"production_ready" boolean is `false`.

## 5. Before returning

- One JSON object, all `required_top_level_keys`, no prose.
- Enum values copied verbatim from the template.
- Lists obey `ordering_rules`; category-code lists sorted ascending and upper-cased.
- Whole-integer counts; `0` (not null) where the template says "0 when not applicable".
- A summary count equals the length/derivation of the list it describes.
