# Data hygiene & portfolio-category resolution

These rules recur across every task type. They are general conventions of the environment, not
task-specific answer values.

## 1. Primary vs duplicate
- A work item is a **duplicate** when `duplicate_of` is non-null. It points at the canonical
  **primary** named by `duplicate_of`.
- `duplicate_of` is the **authoritative** duplicate signal — *not* `status`. A duplicate can carry
  `status: "Closed"` (and a stale `mirror_status`/`legacy_category`), so do not rely on status to
  detect duplicates.
- Duplicates are **reported, never counted**:
  - Report them in the schema's duplicate/exclusion field — e.g. `duplicate_clusters`
    (`{primary_id, duplicate_ids:[...]}`), `excluded_duplicate_ids`, or a combined
    `excluded_distractor_ids` field (some schemas lump duplicates + cancelled + distractors
    together — follow the schema you are given).
  - Exclude them from `included_*_ids`, `category_counts`, percentages, aging buckets, overdue
    sets, severity counts, milestone denominators, and every total.
  - The **primary** is the record that duplicates point *at*; it is counted once.

## 2. Authoritative fields over stale mirrors
- Use the authoritative `status` field for lifecycle state.
- Resolve portfolio category from `work_type` / `labels` / `title`. **Ignore** `mirror_status` and
  `legacy_category` — they are stale mirror/export fields (a record may even be labeled
  `stale-export`).
- Where the schema requires an acknowledgement, set it (e.g.
  `ignored_mirror_status_and_legacy_category: true`).

## 3. Exclude cancelled
- In-scope records with `status: "Cancelled"` are excluded from primary counts. Report them where
  the schema provides a field (e.g. `excluded_cancelled_ids`, or a combined exclusion field).

## 4. Exclude distractors
- Records that look in-scope (same quarter / product area / team) but are **not primary closed
  portfolio work** are distractors — e.g. duplicates, cancelled items, or same-scope records that
  fail the inclusion criteria. Exclude them and report them in the schema's exclusion field(s).
  Which records count as "distractors" vs "duplicates" vs "cancelled" is dictated by the schema's
  field set — match the schema's structure exactly.

## 5. Inclusion criteria
- **Closed/complete**: determine the terminal status set from the task's closed-window semantics
  (typically `Closed, Done, Deployed, Verified`). `Cancelled` and `Duplicate` are never included.
- **In-scope**: the prompt's teams, product area(s), quarter (mix tasks) or as-of + closed window
  (SLA tasks), and category set.
- **Primary**: `duplicate_of` is null.
- Apply all three filters; the survivors are the included primary set used for every denominator.

## 6. Portfolio-category resolution
Classify each included primary item into **exactly one** of `NewFeature, TechDebt, Reliability,
Security`. Aggregate category signals from three sources, then pick the highest-precedence category
for which **any** signal is present.

**Signal sources (priority of source, for tie-breaking within a category):** `work_type` → `labels`
→ `title`. `legacy_category` and `mirror_status` are **not** sources.

**Category precedence (highest wins):** `Security` > `Reliability` > `TechDebt` > `NewFeature`.

### Signal → category table
| Category | `work_type` | `labels` (any of) | `title` (keywords) |
|---|---|---|---|
| **Security** | `Security`, `Compliance` | `security`, `cve`, `auth`, `encryption` | security, cve, auth, encryption |
| **Reliability** | `Reliability`, `Incident` | `reliability`, `latency`, `outage`, `incident`, `flaky` | reliability, latency, outage, incident, flaky, stabilize |
| **TechDebt** | `Refactor`, `Chore`, `Dependency` | `cleanup`, `refactor`, `migration`, `tech-debt` | cleanup, refactor, migration, deprecate |
| **NewFeature** | `Feature`, `Enhancement` | `feature`, `rollout` | feature, rollout (generic new work) |

### How to apply
1. Collect every signal the item emits across `work_type`, `labels`, and `title` (parse `labels`
   from its JSON-text form).
2. Map each signal to its category via the table.
3. If multiple categories are indicated, choose by precedence
   `Security > Reliability > TechDebt > NewFeature`.
4. The result is the item's single portfolio category.

### Notes / traps
- `work_type: Bug` is **not** itself a category signal — defer to `labels`/`title` (a `Bug` with a
  `reliability`/`flaky` label is `Reliability`).
- A `feature`/`rollout` label does **not** force `NewFeature` if a higher-precedence signal is
  present (e.g. a `security`/`cve` label → `Security`; a `cleanup`/`migration` label or a
  "cleanup"/"migration" title → `TechDebt`).
- A keyword in the **title** can supply the deciding signal (e.g. a "Cleanup …" title on an
  otherwise feature-labeled item → `TechDebt`).
- The word "stale" appearing in a title does **not** negate a `labels` signal — labels are
  authoritative; the "stale" hygiene rule applies to the `mirror_status`/`legacy_category` fields,
  not to labels.

## 7. SLA population (shared with SLA-aging tasks)
- The SLA-relevant population is the included primary set whose resolved portfolio category is
  `Reliability` or `Security` (same resolution as above), filtered to the prompt's teams and
  as-of/closed-window.
- **Overdue** = a primary item past its SLA due horizon as of the as-of date (use
  `sla_policy` `days_to_due` by `severity` against `due_at`/as-of, per the task's stated rule).
- **Missing owner** = included primary with `owner` is `null`.
- **Breach rate** = `overdue_primary_count / included_primary_count`, rounded to exactly 3 decimals.
- Duplicate clusters and missing-owner IDs are reported but duplicates are never counted as primary.
