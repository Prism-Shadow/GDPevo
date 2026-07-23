# Distractor records

Every endpoint returns the full dataset, not just the target slice. Distractor records are
deliberately mixed in to test whether you filter correctly. They fall into a few patterns;

**Identify and exclude them before deciding.**

## Prefix-based distractors
Records whose id uses a different prefix than the targets are almost always unrelated:
- Contractor endpoints include `C-DIS-*` (display), `C-TE1-*`, `C-TE4-*` rows alongside the
  target `C-TR1-*` / `C-TR4-*` rows. Keep only the target prefix (plus related records keyed
  by the target's `prior_license_id` / `related_application_id`).
- Liquor applications include `L-DIS-*`, `L-TE3-*` rows; keep only the named target.
- Alcohol licensees include `AL-DIS-*`, `AL-TE2-*`, `AL-TE5-*` rows alongside the target
  `AL-TR3-*` rows.

## Cross-key collisions (renewal queue)
A target licensee's **address** may be shared by violations filed under a **different
license number** (`AL-TE2-*`, `AL-TE5-*`). These are distractors. Match violations by the
target's own `license_no` (exact) and its `successor_to` old permit (uncertain) only —
**not** by address. Including address-collision rows from other licenses destroys the queue.

## "LATE" / post-feed rows (renewal queue)
Violation rows with id suffix `-LATE` and `source_name == "post_boundary_feed"` fall after
the release boundary. They are **distractors for matching** (do not count or queue them) but
are **not noise to discard silently** — list their ids in
`post_boundary_violation_ids_excluded`.

## "DIS" inspection / correspondence / history rows
Inspection, correspondence, and violation records for a target may carry an id like
`CI-DIS-...`, `COR-DIS-...`, `CV-DIS-...` or reference an unrelated `license_id`
(e.g. `CL-HIST-*`). Whether a `*-DIS-*` record belongs to the target depends on its join
key:
- If it shares the target's `related_application_id` / `license_id`, it is a real
  (if oddly-named) record for that target — include it in the join.
- If its join key points elsewhere, it is a distractor — exclude it.

For the **last/most-relevant** inspection of a contractor target, prefer the inspection
whose id matches the target's own pattern (`CI-C-TR1-...`) over a `CI-DIS-...` row when both
relate to the same application; the `CI-DIS-...` "potential stale export" notes are a hint
to discount that row.

## "Old location name" / inactive-settlement signals (liquor)
A police memo noting an old location name, or an `active: false` settlement, is a
**verification concern**, not grounds to discard the same-premises record or flip the basis
flag. Surface it as a verification gap, but keep the related record in your analysis.

## Operational rule
When a record's id prefix or source feed does not belong to your target's family, or its
join key points to a different entity, exclude it. When it belongs to the target but is
stale/superseded, keep it for context but weight the current/active version for decisions.
