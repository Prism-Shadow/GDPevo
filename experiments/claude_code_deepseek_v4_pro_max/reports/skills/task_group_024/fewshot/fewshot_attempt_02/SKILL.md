# Portfolio Engineering Review Skill

You are an agent that completes portfolio engineering review tasks by interacting with a shared HTTP API environment. Follow these instructions to read the task prompt and answer template, query the environment, compute results, and produce a correctly formatted JSON answer.

---

## 1. Read the Input Files

Each task directory contains:
- `prompt.txt` — the task instructions, including scope parameters (teams, quarter, release id, as-of date, etc.)
- `payloads/answer_template.json` — the required JSON output schema

Read both files. The `prompt.txt` defines the business scope. The `answer_template.json` is a JSON Schema that defines every required field, its type, enum constraints, and ordering/naming conventions. **Your output must validate against this schema exactly.**

---

## 2. Connect to the Environment

The task environment is a REST API. Read `environment_access.md` from the workspace root for the base URL, allowed endpoints, and credentials.

Standard configuration:
- Base URL: `http://task-env:9024/`
- API endpoints are read-only GET except `POST /api/query` for SQL queries
- For `POST /api/query`, include header `X-Env-Token: portfolio-readonly`

**Available GET endpoints:**
| Endpoint | Returns |
|---|---|
| `GET /api/work-items` | All work items (paginated list) |
| `GET /api/work-items/{item_id}` | Single work item detail |
| `GET /api/mix-targets` | Portfolio mix target rows |
| `GET /api/sla-policy` | SLA policy configuration |
| `GET /api/releases` | All releases |
| `GET /api/releases/{release_id}` | Single release detail |
| `GET /api/milestones` | All milestones |
| `GET /api/dependencies` | Dependency records between work items |
| `GET /api/blockers` | Blocker records on work items |

**POST endpoint:**
| Endpoint | Purpose |
|---|---|
| `POST /api/query` | Run a restricted SQL query against the environment database. Send header `X-Env-Token: portfolio-readonly`. |

Use `curl` or an HTTP library to call these endpoints. Fetch all relevant data before computing results.

---

## 3. Task Type Reference

There are three distinct review types. Match your approach to the prompt's intent.

### 3A. Portfolio Mix Review

**Goal:** Classify closed work items into portfolio categories, compare the resulting count-based mix with target percentages, and identify rebalance actions.

**Data sources:**
- `GET /api/work-items` — fetch in-scope work items
- `GET /api/mix-targets` — fetch the target mix row for the given `scope_id`

**Scope filtering:** Filter work items by the scope parameters from the prompt: teams, product areas, quarter. For quarter filtering, use the work item's `closed_at` or other date fields — match items that closed within the specified quarter.

**Portfolio categories (exactly four):**
- `NewFeature`
- `TechDebt`
- `Reliability`
- `Security`

**Category assignment priority for conflicting signals:**
When a work item has multiple signals pointing to different categories, resolve conflicts using this priority order:
1. **`portfolio_category` field** on the work item (authoritative, if present and valid)
2. **`type` field** — maps to categories via the work item type convention
3. **`labels` array** — check for category-indicating label values
4. **`title`** — as a last resort, scan for category keywords

When two or more plausible signals conflict, prefer the highest-priority signal. If a work item lacks any signal, flag it for review but do not silently assign a category.

**Inclusion rules:**
- Include only **closed** work items matching the scope
- Exclude items with status `cancelled` or `duplicate`
- Track excluded items separately in the exclusion flags
- Count each included item exactly once

**Duplicate detection:**
- A work item is a duplicate if its `status` field is `duplicate` or its `type` field is `duplicate`, or if its `duplicate_of` / `primary_item_id` field points to another work item
- Duplicate items contribute to `excluded_duplicate_ids`
- Duplicates are NOT counted in category counts or percentages

**Cancelled items:**
- Items with status `cancelled` go to `excluded_cancelled_ids`
- These are NOT counted in category counts or percentages

**Stale mirror fields:**
- Some work items may have `mirror_status` or `legacy_category` fields — ignore these
- Use only the authoritative work item fields (status, type, portfolio_category, labels, title)
- Always set `ignored_mirror_status_and_legacy_category` to `true` in exclusion flags

**Distractor records:**
- Records matching the scope (same team/product area/quarter) but not meeting inclusion criteria go to `excluded_distractor_ids`
- Common distractors: items that are not closed, items with mismatched scope, items that look in-scope but have a different actual scope

**Computing the mix:**
1. Count included items per category → `category_counts`
2. Compute percentages: `(category_count / total_included) * 100`, rounded to 1 decimal place → `category_percentages` or `actual_pct`
3. Read target percentages from the mix-targets row for the scope → `target_pct`
4. Compute gaps: `gap_pct = actual_pct - target_pct`, rounded to 1 decimal place
5. Identify under-invested categories: those with negative `gap_pct`, ordered from most negative to least negative

**Follow-up / recommended action:**
- If any category has a negative gap: action = `REBALANCE_CAPACITY`
- `primary_category` = the category with the largest negative gap
- `secondary_category` = the category with the second largest negative gap (or null if only one)
- `rationale_code` = `LARGEST_NEGATIVE_GAP`
- If no negative gaps: action = `MAINTAIN_CURRENT_MIX`, rationale = `NO_NEGATIVE_GAPS`
- If data conflicts prevent confident analysis: action = `INVESTIGATE_DATA_QUALITY`, rationale = `DATA_CONFLICT`
- When the answer template includes an `owner_team` field on the recommended action: pick the team from scope with the most items in the deficit category

**Output ordering:**
- `included_work_item_ids`: sort by `closed_at` ascending, then by `id` ascending
- `gap_table` / `mix_table` rows: always in this fixed order: NewFeature, TechDebt, Reliability, Security
- `under_invested_categories`: most negative gap first
- `excluded_*_ids`: sort by `closed_at` ascending, then `id` ascending
- Team arrays: sort alphabetically

---

### 3B. SLA Aging Audit

**Goal:** Identify SLA-relevant work items, separate primary from duplicate records, calculate aging, find hotspots, and compute breach rate.

**Data sources:**
- `GET /api/work-items` — fetch work items for the specified teams
- `GET /api/sla-policy` — fetch SLA policy configuration (deadlines by severity, category rules)

**Scope filtering:**
- Filter by the teams listed in the prompt
- Filter by the SLA categories (typically `Reliability` and `Security`)
- Use the `as_of` date from the prompt as the reference date for all age calculations
- Use `recent_closed_window_days` to identify recently-closed items (not overdue if closed within this window)

**Primary vs. duplicate:**
- **Primary records** are the canonical work items — use the work item's own status and fields
- **Duplicate records** have `status: "duplicate"` or a `duplicate_of` / `primary_item_id` reference pointing to a primary
- Duplicates form clusters: each cluster has one `primary_id` and a list of `duplicate_ids`
- Duplicates are excluded from primary counts (included_primary_ids, overdue counts, aging, missing owners, breach rate)
- Report duplicate clusters in `duplicate_clusters`

**SLA categories for work items:**
When the prompt says to use portfolio category conventions for resolving conflicting signals, apply the same priority as in 3A: `portfolio_category` field > `type` field > `labels` > `title`.

**SLA overdue determination:**
1. Read SLA policy to get the allowed age (in days) for each severity level (S1, S2, S3, S4)
2. For each included primary work item, compute its age: `as_of_date - created_date` (in days)
3. An item is overdue if `age > sla_deadline_days` for its severity level AND it is not closed within the recent window
4. Recently closed items (closed within `recent_closed_window_days` of `as_of`) are NOT overdue

**Aging distribution:**
- Compute age for all included primary items: `age = as_of_date - created_date` in days
- Bucket into: 0-3, 4-7, 8-14, 15-30, 31+ days
- Count primary items in each bucket

**Team overdue counts:**
- Group overdue primary items by team
- Count per team
- List alphabetically by team name

**Hotspot detection:**
- Group overdue primary items by (team, owner) pairs
- The hotspot is the pair with the most overdue items
- If owner is missing/null/empty, use `UNASSIGNED`
- Report: `team`, `owner`, `overdue_count`

**Overdue by severity:**
- Group overdue primary items by severity level (S1, S2, S3, S4)
- Count per severity

**Escalation queue:**
- Sort overdue primary items into escalation order
- Priority: S1 first, then S2, then S3, then S4
- Within the same severity, order by age descending (oldest first)

**Missing owners:**
- Primary included items with null, empty, or missing `owner` / `assigned_to` field
- List their IDs sorted ascending

**Breach rate:**
- `breach_rate = overdue_primary_count / included_primary_count`
- Round to exactly 3 decimal places
- If `included_primary_count` is 0, breach rate is 0.000

**Output ordering:**
- `included_primary_ids`: sorted lexicographically ascending
- `overdue_primary_ids`: sorted lexicographically ascending
- `missing_owner_ids`: sorted lexicographically ascending
- `duplicate_clusters`: sorted by `primary_id` ascending; within each cluster, `duplicate_ids` sorted lexicographically
- `team_overdue_counts`: teams listed alphabetically

---

### 3C. Release Readiness Assessment

**Goal:** Evaluate whether a release is ready to ship based on milestone completion, blockers, and dependencies.

**Data sources:**
- `GET /api/releases/{release_id}` — fetch the specific release
- `GET /api/milestones` — fetch all milestones, filter to those belonging to the release
- `GET /api/work-items` — fetch work items linked to the release and its milestones
- `GET /api/blockers` — fetch blocker records for release work items
- `GET /api/dependencies` — fetch dependency chains affecting release work items

**Authoritative data rule:**
Use release, milestone, and work item endpoints as the source of truth. Do not rely on stale mirror/export fields that may appear on work items. The release endpoint's data is authoritative for release state; the milestone endpoint's data is authoritative for milestone state.

**Milestone completion:**
1. For each milestone in the release, identify all primary work items linked to it
2. Count how many of those work items are in a completed/closed status → `complete_primary`
3. Count total primary work items for the milestone → `primary_total`
4. Compute: `completion_pct = (complete_primary / primary_total) * 100`, rounded to 1 decimal place
5. If `primary_total` is 0, `completion_pct` is 100.0 (an empty milestone is trivially complete)
6. Sort `milestone_completion` array by `milestone_id` ascending

**Gating work items:**
- Work items linked to the release that are NOT in a completed/closed status
- These items block release readiness
- List their IDs sorted ascending, no duplicates
- An empty list is valid if all release work items are complete

**Blocker analysis:**
- Fetch blocker records linked to release work items
- Filter to **high-impact** blockers only (check blocker `impact` or `severity` field for "high" or equivalent)
- Filter to **unresolved** blockers (status is not "resolved" or equivalent)
- Group by exact `cause` text string
- Count occurrences per cause
- Report as `blocker_cause_counts`: an object keyed by exact cause text → integer count
- An empty object `{}` is valid if no unresolved high-impact blockers exist

**Critical dependency chains:**
- A dependency chain exists when a release work item `depends_on` another work item
- Follow the chain transitively: if A depends on B, and B depends on C, the chain is [A, B, C]
- A chain is "critical" if the final item in the chain is non-complete
- Each chain is an ordered array of work item IDs: from the blocked release item → through intermediate items → to the non-complete dependency at the end
- Sort chains lexicographically by the full path (compare each element in sequence)
- An empty array `[]` is valid if no critical chains exist

**Ship decision:**
- `SHIP` — all milestones at 100%, no gating work items, no unresolved high-impact blockers, no critical dependency chains
- `NO_SHIP` — one or more milestones below 100%, OR gating work items present, OR unresolved high-impact blockers present, OR critical dependency chains exist
- `SHIP_WITH_WATCH` — all milestones at or near 100% with only minor gaps, no critical blockers, but some watch items exist (e.g., low-impact blockers or minor dependency concerns)

**Readiness score:**
- `readiness_score = total_completed_primary / total_primary_denominator`
- Where `total_completed_primary` = sum of `complete_primary` across all milestones
- Where `total_primary_denominator` = sum of `primary_total` across all milestones
- Round to exactly 3 decimal places
- If denominator is 0, score is 1.000

---

## 4. General Data Conventions

### Sorting Rules
Apply these consistently unless the answer template specifies otherwise:
- **Work item ID lists**: sort lexicographically (string sort, not numeric)
- **Team names**: sort alphabetically
- **Category rows** (gap_table / mix_table): always in fixed order: NewFeature, TechDebt, Reliability, Security
- **Under-invested categories**: most negative gap first (ascending by gap_pct)
- **Duplicate clusters**: by `primary_id` ascending; `duplicate_ids` within each cluster sorted ascending
- **Milestone completion**: by `milestone_id` ascending
- **Dependency chains**: lexicographically by the full ID path
- **Escalation queue**: by severity (S1 > S2 > S3 > S4), then by age descending within severity

### Rounding Rules
- **Percentages** (completion_pct, actual_pct, target_pct, gap_pct): round to **1 decimal place**
- **Rates** (breach_rate, readiness_score, sla_breach_rate): round to **3 decimal places**
- Use standard rounding (half-up): e.g., 0.6666... rounds to 0.667 at 3 decimal places; 33.333... rounds to 33.3 at 1 decimal place

### ID Format
Work item IDs follow the pattern `WI-24024-XXXX` where XXXX may be numeric or alphanumeric with a letter prefix (e.g., `WI-24024-P###`, `WI-24024-S###`, `WI-24024-###`). Sort these as strings.

### Primary vs. Non-Primary
The environment may contain different categories of non-primary records:
- **Duplicates**: records with `status: "duplicate"` or pointing to another item via `duplicate_of` / `primary_item_id`
- **Cancelled**: records with `status: "cancelled"`
- **Distractors**: records in scope by team/quarter but not meeting all inclusion criteria

Always separate primary from non-primary before computing counts, percentages, or rates.

---

## 5. Querying with POST /api/query

When the GET endpoints don't provide sufficient filtering and you need to query across multiple dimensions, use `POST /api/query`:

```bash
curl -s -X POST http://task-env:9024/api/query \
  -H "Content-Type: application/json" \
  -H "X-Env-Token: portfolio-readonly" \
  -d '{"query": "SELECT ... FROM ... WHERE ..."}'
```

The database schema mirrors the API resource model. Common tables include `work_items`, `mix_targets`, `sla_policy`, `releases`, `milestones`, `dependencies`, `blockers`. Inspect the GET responses to understand column names and types before writing queries.

Use this endpoint when you need to:
- Filter work items by multiple criteria simultaneously (team + quarter + category)
- Join across resources (e.g., work items with milestones)
- Find duplicates referencing primary items
- Compute aggregations server-side

---

## 6. Output Requirements

1. Return **only** the JSON object — no explanatory prose before or after
2. Every key in the answer template schema must be present
3. No additional keys beyond what the schema defines (`additionalProperties: false`)
4. All `required` fields must be populated
5. Enum values must match exactly (case-sensitive)
6. Array lengths must respect `minItems` / `maxItems` constraints
7. String patterns must match (e.g., work item ID format)
8. Use `const` values from the schema exactly as specified

---

## 7. Common Pitfalls

- **Don't count duplicates as primary work.** Always check status and duplicate_of/primary_item_id fields first.
- **Don't trust stale mirror fields.** Some work items have `mirror_status` or `legacy_category` — use the authoritative fields instead.
- **Don't round intermediate values.** Only round the final output values as specified. Compute percentages from exact counts.
- **Don't assume all items in a team's scope are primary.** Filter by status (closed for portfolio mix, non-duplicate for SLA).
- **Don't include cancelled items in counts.** They are exclusions.
- **Don't sort work item IDs numerically.** Use lexicographic (string) ordering unless specifically told otherwise.
- **Don't reorder fixed category arrays.** NewFeature, TechDebt, Reliability, Security always in that order.
- **Don't omit empty arrays/objects.** If there are no duplicates, blockers, or dependency chains, return `[]` or `{}` — never omit the key.
- **Don't compute SLA age from the wrong date.** Age = `as_of` - `created_date`. Don't use `updated_date` or `closed_date` for age.
- **Don't treat recently-closed items as overdue.** Items closed within the recent window are resolved, not overdue.
