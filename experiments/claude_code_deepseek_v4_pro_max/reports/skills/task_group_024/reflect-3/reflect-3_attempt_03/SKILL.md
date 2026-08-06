# Portfolio Engineering Analysis Skill

Use this skill whenever the task involves portfolio-mix analysis, SLA-aging audits, or release-readiness assessments against a shared engineering-work-item environment. It encodes the conventions learned from portfolio-review and SLA-audit tasks so you can classify work items, compute mix metrics, surface overdue work, and assess release readiness without rediscovering the rules each time.

---

## Environment Access

The task environment exposes a set of REST endpoints through `{BASE_URL}`. The runtime supplies the base URL and any required tokens separately — do not hardcode them.

Available endpoints typically include:
- `GET /api/work-items` — paginated or full list of work items
- `GET /api/work-items/{item_id}` — single item detail
- `GET /api/mix-targets` — portfolio mix targets by scope
- `GET /api/sla-policy` — severity-to-days SLA mapping
- `GET /api/releases` — release trains
- `GET /api/milestones` — milestones keyed to releases
- `GET /api/dependencies` — inter-item dependency edges
- `GET /api/blockers` — blocker records keyed to work items and releases
- `POST /api/query` — restricted SQL read-only queries (token required)

When the environment provides a token, it goes into a header on every call. Read `environment_access.md` (if present) for exact header names and token values.

**Data-authority rule:** The `status`, `work_type`, `labels`, `closed_at`, `created_at`, `duplicate_of`, `severity`, and `owner` fields on work items are authoritative. The `mirror_status` and `legacy_category` fields are stale mirror/export artifacts — ignore them for classification and status decisions. Use `closed_at` (not `mirror_status`) to decide whether an item was resolved by a given date.

---

## Portfolio Category Classification

Every work item must be assigned to exactly one of four portfolio categories: **NewFeature**, **TechDebt**, **Reliability**, **Security**. Use the following precedence-ordered rules.

### Step 1 — Label-keyword check (highest priority)

Look for these keywords in the item's `labels` array (case-insensitive):

| Keyword group | Category |
|---|---|
| `security`, `cve` | **Security** |
| `reliability`, `incident`, `outage`, `latency` | **Reliability** |

If **any** Security keyword is present → **Security**.  
Else if **any** Reliability keyword is present → **Reliability**.  
Only `security` and `cve` trigger Security; `auth` and `encryption` alone do **not**.

### Step 2 — Legacy-category fallback

If no label keyword matched, check `legacy_category` (the field exists but is secondary to labels):

| `legacy_category` value | Maps to |
|---|---|
| `security` | **Security** |
| `tech-debt` | **TechDebt** |

The value `maintenance` is **not** a category signal — skip it and proceed to Step 3.  
The value `new`, `quality`, `bug`, `admin`, `feature`, `incident`, `release` carry no category signal either.

### Step 3 — Work-type mapping (lowest priority)

| `work_type` | Category |
|---|---|
| `Security`, `Compliance` | **Security** |
| `Reliability`, `Incident` | **Reliability** |
| `Feature`, `Enhancement` | **NewFeature** |
| `Refactor`, `Chore`, `Bug` | **TechDebt** |
| `Dependency` | **TechDebt** (unless `legacy_category` = `security` → Security) |

---

## Work-Item Filtering

### Portfolio-mix tasks
- Filter by: team(s), product_area(s), **quarter** (closed_at in the quarter's date range).
- **Exclude:** items with `status = "Duplicate"`, items where `duplicate_of` is non-null (they point to another work item), and items with `status = "Cancelled"`.
- An item can have `status = "Closed"` but still be a duplicate if `duplicate_of` is set — exclude it.
- Report excluded duplicates and cancelled items separately (exclusion flags or distractor lists).
- Sort included items by `closed_at` ascending, then `id` ascending.

### SLA-aging tasks
- Filter by: team(s), portfolio categories (Reliability and/or Security), `created_at <= as_of_date`.
- **Exclude:** duplicates (same rules as above) and cancelled items.
- **Include only** items that are either:
  - Still open as of the as-of date (`closed_at` is null or `closed_at > as_of_date`), **or**
  - Recently closed (`closed_at` between `as_of_date - recent_closed_window_days` and `as_of_date` inclusive).
- Items closed before the recent-closed-window cutoff are excluded from the primary population.
- Sort ID lists lexicographically (ascending).

### Release-readiness tasks
- Filter by: `release_id`.
- **Exclude:** items with `status = "Duplicate"` (they are not primary work).
- "Complete" statuses: `Closed`, `Done`, `Deployed`, `Verified`.
- "Incomplete" statuses: `Backlog`, `In Progress`, `Review`, `Reopened`.

---

## SLA Aging Calculations

### SLA policy (standard)
| Severity | Days to due |
|---|---|
| S1 | 3 |
| S2 | 10 |
| S3 | 21 |
| S4 | 45 |

### Overdue determination
An item is overdue if it breached its SLA deadline. Compute the deadline as `created_at + sla_days`.

- **Open items** (not closed, or closed after as_of): overdue if `as_of_date > deadline`.
- **Recently closed items** (closed on or before as_of): overdue if `closed_at > deadline` (resolved late).

### Aging distribution
Compute age for each primary item:
- If the item was **closed on or before the as-of date**: `age = (closed_at - created_at)` in days (resolution time).
- If the item is **still open** (no `closed_at`, or `closed_at > as_of_date`): `age = (as_of_date - created_at)` in days (current age).

Bucket ages into: **0–3**, **4–7**, **8–14**, **15–30**, **31+** days.

### Breach rate
`breach_rate = overdue_primary_count / included_primary_count`, rounded to exactly **3 decimal places**.

### Escalation queue (SLA tasks with escalation)
Order overdue primary items by severity (S1 first, then S2, S3, S4), then within each severity by age descending (oldest unresolved first). For recently-closed overdue items, use resolution time for age comparison.

### Owner hotspot
Count overdue primary items grouped by `(team, owner)`. If `owner` is null, use `"UNASSIGNED"`. The hotspot is the pair with the highest count. Ties are broken alphabetically by team, then by owner name.

### Missing-owner IDs
List primary (included) items where `owner` is null, sorted lexicographically.

---

## Release Readiness

### Ship decision heuristics
- **NO_SHIP** — any unresolved Critical-severity blocker.
- **SHIP_WITH_WATCH** — unresolved High-severity blockers, or incomplete gating items remain but no Critical blockers.
- **SHIP** — no unresolved High or Critical blockers and all items are complete.

### Milestone completion
For each milestone (sorted by `milestone_id` ascending):
- `primary_total` = count of primary work items assigned to that milestone.
- `complete_primary` = count of those items in a complete status.
- `completion_pct` = `(complete_primary / primary_total) * 100`, rounded to **1 decimal place**.

### Gating work items
All incomplete primary items in the release, sorted ascending with no duplicates.

### Blocker cause counts
Count only **unresolved** (`status = "Open"`) blockers with **high impact** (`severity = "High"` or `"Critical"`), keyed by exact `cause` string. Ignore `Low`/`Medium` severity and non-Open statuses (e.g., `Monitoring`, `Resolved`).

### Critical dependency chains
Only `"blocks-release-readiness"` dependency relations matter. For each **incomplete** release work item, trace the dependency chain through `depends_on_id` links. A chain is critical only if the final dependency is a **non-complete**, **non-duplicate** item. If the dependency is a `Duplicate`, the chain is not reportable (the duplicate has no primary work behind it). Sort chains lexicographically by their full path representation.

### Readiness score
`readiness_score = complete_primary_count / primary_total_count`, rounded to exactly **3 decimal places**.

---

## Mix Table Computations

### Percentages and gaps
For each category in order **NewFeature, TechDebt, Reliability, Security**:
- `actual_pct` = `(category_count / total_included) * 100`, rounded to **1 decimal place**.
- `target_pct` = from the mix-target row (multiply the fractional values by 100 to get percentage points).
- `gap_pct` = `actual_pct - target_pct`, rounded to **1 decimal place**.

### Under-invested categories
Categories where `gap_pct < 0`, sorted from most negative gap to least negative.

### Follow-up / recommended action
- If any category has a negative gap → `REBALANCE_CAPACITY`, with `primary_category` = the most negative gap category and `secondary_category` = the second most negative (or null).
- Rationale: `LARGEST_NEGATIVE_GAP`.
- For portfolio-mix tasks that ask for an owner team, select the team with the larger capacity need for the deficit category.

---

## Sorting and Precision Conventions

| Context | Convention |
|---|---|
| Work-item ID lists | Lexicographic ascending (`WI-24024-001` < `WI-24024-002` < `WI-24024-P001`) |
| Team lists | Alphabetical ascending |
| Milestone lists | By `milestone_id` ascending |
| Included portfolio items | By `closed_at` ascending, then `id` ascending |
| Duplicate clusters | By `primary_id` ascending; `duplicate_ids` within each cluster sorted ascending |
| Gap table / mix table rows | Fixed order: NewFeature, TechDebt, Reliability, Security |
| Percentages | Rounded to **1 decimal place** (percentage points) |
| Breach / readiness rates | Rounded to **3 decimal places** |

---

## Common Pitfalls

1. **Don't trust `mirror_status`.** An item whose `mirror_status` says "Open" may actually be "Verified" — use `status`.
2. **Don't trust `legacy_category` for classification.** It is a secondary signal at best; labels and `work_type` take priority.
3. **`duplicate_of` beats `status`.** An item with `status = "Closed"` but a non-null `duplicate_of` is a duplicate — exclude it from primary counts.
4. **Cancelled items are never primary.** Exclude them regardless of `closed_at`.
5. **The `maintenance` legacy category is not a TechDebt signal.** It carries no category meaning — fall through to work_type.
6. **Future-dated items don't belong.** Items with `created_at > as_of_date` cannot be in an SLA or portfolio population — they didn't exist yet.
7. **Aging for closed items uses resolution time, not current age.** For items resolved by the as-of date, the metric is how long they took to close, not how old they would be if still open.
