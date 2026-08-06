# Signal vs Noise Detection

Every matter is seeded with distractor records that look plausible but must be excluded.
Use **all three** checks; the remediation-actions cross-check is authoritative.

## 1. ID naming convention (fast first filter)

| Pattern | Example | Class |
|---|---|---|
| `{TYPE}-{SHORTCODE}-{DESCRIPTOR}` | `SRC-SENT-ALDEN-PHONE`, `PRIV-NORTH-LOG-GAP`, `QC-GRAY-MISCODED-PRIV`, `RET-ALLOY-BOX-POST`, `DOC-ALLOY-BID-EMAIL-1` | **Signal** |
| `{TYPE}-{MATTERCODE}-NNN` | `SRC-SENTINELGJ-001`, `PRIV-GRAYCLIFFS-002`, `RET-HARBORSTON-003`, `DOC-NORTHBAYSE-0001` | **Noise** |

`SHORTCODE` is a 3–5 letter stem (`SENT`, `GRAY`, `NORTH`, `ALLOY`, `HARB`).
`MATTERCODE` is the full uppercased matter stem (`SENTINELGJ`, `GRAYCLIFFS`, `NORTHBAYSE`,
`ALLOYWORKS`, `HARBORSTON`).

SQL filter to drop noise:
```sql
WHERE source_id NOT LIKE '%-<MATTERCODE>-%'
```

## 2. Noise-note catalog

Records with any of these `notes` are distractors (even if their ID looks borderline):

- "routine"
- "No production-impacting issue has been escalated yet"
- "Review team marked this item for follow-up but not immediate remediation"
- "Privilege sample has ordinary review variance"
- "Entry included to create similar labels across matters"
- "Finding is similar to escalated records in another matter"
- "Review manager requested re-sampling before escalation"
- "Potential issue was remediated by archive collection"  (already remediated — not an open gap)
- "Source map entry has minor metadata normalization issues"
- "Collection status differs between custodian tracker and vendor load report"
- "Requires matter-level filtering because similar issue labels appear across matters"
- "Vendor tracker and legal hold tracker use slightly different record labels"
- "Retention entry is relevant only after comparing hold date and policy period" (often a distractor; verify against dates)

## 3. Remediation-actions cross-check (authoritative)

```sql
SELECT action_id, action_type, priority, severity, owner, target_ref, due_days
FROM remediation_actions WHERE matter_id='<M>'
```

- **Non-noise** actions (`ACT-<MATTERCODE>-NNN` with no `NOISE` token) target signal records.
  The set of `target_ref` values = the signal record IDs to surface as findings/risks and
  the basis for the action plan.
- **Noise** actions have `NOISE` in `action_id` and description
  "Routine action included as realistic operational noise." They target category codes
  (e.g. `SEC-E`, `F`), not record IDs — exclude them.

If a record is named like a signal record (check 1) AND appears as a non-noise
`target_ref` (check 3), it is signal. If the checks disagree, trust check 3.

## Consequence of getting this wrong

- Including a noise record as a finding → that finding won't match gold (wrong/extra record).
- Counting noise records in metrics → metric values wrong; with all-or-nothing metric
  scoring, one wrong metric can fail the whole metrics block.
- Missing a signal record → missing finding + wrong category/action counts.

Always compute the signal set first, then build every section and metric from it.
