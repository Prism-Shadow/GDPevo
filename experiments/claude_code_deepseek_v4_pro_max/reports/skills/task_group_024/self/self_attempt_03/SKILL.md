# Portfolio Engineering Audit Skill

Perform portfolio engineering audits across three analysis types: portfolio mix analysis,
SLA aging audits, and release readiness assessments. This skill encodes reusable operating
rules distilled from audit patterns observed in engineering portfolio environments.

---

## 1. Environment Protocol

### 1.1 Startup
Before any analysis, read the file `environment_access.md` in the working directory. It
provides the runtime base URL, credentials, and the list of allowed API endpoints. The
base URL overrides any localhost or `env/setup.sh` references found in task prompts.

### 1.2 Authentication
For the `POST /api/query` endpoint only, include the header specified in
`environment_access.md` (typically `X-Env-Token` with the listed token value). All `GET`
endpoints are unauthenticated.

### 1.3 Typical Endpoint Inventory
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/work-items` | List all work items |
| GET | `/api/work-items/{item_id}` | Fetch a single work item |
| GET | `/api/mix-targets` | Portfolio mix target percentages |
| GET | `/api/sla-policy` | SLA thresholds per category/severity |
| GET | `/api/releases` | List releases |
| GET | `/api/releases/{release_id}` | Fetch a single release |
| GET | `/api/milestones` | Milestones for releases |
| GET | `/api/dependencies` | Work item dependency edges |
| GET | `/api/blockers` | Blocker records |
| POST | `/api/query` | Restricted SQL/structured query (authenticated) |

Not every task uses every endpoint. Use only those relevant to the analysis type.

### 1.4 Output Rule
Always return a single JSON object. Never include prose, markdown fences, or commentary
outside the JSON structure. Match the provided answer template exactly.

---

## 2. Work Item Data Model

Work items share these fields across all analysis types. Prefer **authoritative** fields
over mirror, export, or legacy fields. When a mirror field disagrees with the
authoritative field, trust the authoritative source.

| Field | Description | Used In |
|-------|-------------|---------|
| `id` | Unique work item identifier (e.g. `WI-24024-A001`) | all |
| `status` | Current status: `closed`, `open`, `in_progress`, `cancelled`, `duplicate` | all |
| `type` / `category` | Portfolio category: `NewFeature`, `TechDebt`, `Reliability`, `Security` | mix, sla |
| `team` | Owning engineering team | all |
| `product_area` | Product area label | mix |
| `owner` | Assigned owner (may be null/UNASSIGNED) | sla |
| `closed_at` | ISO-8601 close timestamp | mix, sla |
| `created_at` | ISO-8601 creation timestamp | sla |
| `severity` | Severity tier: `S1`, `S2`, `S3`, `S4` | sla |
| `quarter` | Planning quarter (e.g. `2025-Q4`) | mix |
| `release_id` | Associated release identifier | release |
| `milestone_id` | Associated milestone identifier | release |
| `duplicates` / `duplicate_of` | Duplicate relationship (array or reference) | sla |

### 2.1 Mirror / Stale Field Rule
Some work items carry mirror status fields or legacy category fields from export/sync
processes. These may be stale. Always resolve classification and status from the
authoritative fields, not from mirror or legacy columns. Ignore `mirror_status` and
`legacy_category` when the authoritative source is available.

---

## 3. Portfolio Category Classification

### 3.1 Standard Categories
Work items are classified into exactly one of four portfolio categories:

1. **NewFeature** — net-new user-facing or internal capabilities
2. **TechDebt** — refactoring, code quality, technical modernization
3. **Reliability** — availability, performance, resilience, incident follow-up
4. **Security** — vulnerabilities, security hardening, compliance

### 3.2 Conflict Resolution
When type, label, or title signals disagree on category:

1. Prefer the authoritative `type` or `category` field.
2. If the type field is missing or ambiguous, resolve from `labels` tags.
3. If labels are ambiguous, inspect the `title` for category-signal keywords.
4. Security and Reliability take precedence over TechDebt when the item addresses a
   security vulnerability or an incident follow-up, respectively.

### 3.3 Mixed-Signal Tiebreaker
When an item touches multiple categories (e.g. security-themed refactoring), classify
by the **primary intent** evident from the title and description. The primary intent is
the problem being solved, not the implementation technique.

---

## 4. Portfolio Mix Analysis

Applies to: train_001, train_004 pattern tasks.

### 4.1 Scoping
Filter the closed work item population by:

- **Quarter** — exact match on the planning quarter field
- **Teams** — items owned by any of the named teams
- **Product areas** — items in any of the named product areas
- **Status** — only `closed` items count toward the portfolio mix

Use the `mix_targets` row whose `scope_id` matches the task's scope identifier. The
target row provides the target percentage for each portfolio category.

### 4.2 Inclusion / Exclusion

**Include** as primary closed work: items that meet all scope criteria and are not
excluded by any rule below.

**Exclude** (but record in exclusion flags):
- **Duplicates** — items whose status or relationship field indicates they are a
  duplicate of another work item. Record their IDs in `excluded_duplicate_ids`.
- **Cancelled** — items with `cancelled` status. Record in `excluded_cancelled_ids`.
- **Distractors** — items that appear to be in scope (same quarter, teams, product
  area) but are not primary closed portfolio work (e.g. they are open, duplicate, or
  belong to a different classification axis). Record in `excluded_distractor_ids`.

### 4.3 Mix Calculation
For included items only:

1. Count items per category → `category_counts`
2. Compute actual percentage per category:
   `actual_pct = round((count / total_included) * 100, 1)`
3. Compute gap per category:
   `gap_pct = round(actual_pct - target_pct, 1)`
4. Under-invested categories: categories where `gap_pct < 0`, ordered from most
   negative gap to least negative gap.

### 4.4 Follow-Up Action Selection
Select exactly one controlled follow-up action:

| Condition | Action | Rationale Code |
|-----------|--------|----------------|
| Any category has a negative gap | `REBALANCE_CAPACITY` | `LARGEST_NEGATIVE_GAP` |
| No negative gaps exist | `MAINTAIN_CURRENT_MIX` | `NO_NEGATIVE_GAPS` |
| Data conflict prevents reliable calculation | `INVESTIGATE_DATA_QUALITY` | `DATA_CONFLICT` |

When `REBALANCE_CAPACITY`, set `primary_category` to the category with the largest
negative gap and `secondary_category` to the category with the second-largest negative
gap (or `null` if only one category is under-invested).

When `MAINTAIN_CURRENT_MIX`, set both `primary_category` and `secondary_category` to
`null`.

### 4.5 Recommended Action (train_004 variant)
When the template uses `recommended_action` instead of `follow_up_action`:
- `action` is always `REBALANCE_CAPACITY`
- `category` is the `largest_deficit_category` (most negative gap)
- `owner_team` is the team with the most items in the deficit category among the scoped
  teams

---

## 5. SLA Aging Audit

Applies to: train_002, train_005 pattern tasks.

### 5.1 Scoping
Filter work items by:

- **Teams** — items owned by any of the named teams (case-sensitive exact match)
- **Categories** — portfolio categories to include (typically `Reliability` and
  `Security`)
- **Status** — include all non-cancelled items for the population scan

### 5.2 Primary vs Duplicate Separation

**Primary records**: work items that are not marked as duplicates and are not
referenced as duplicates by other items.

**Duplicate clusters**: when work item A references work item B as its primary
(duplicate of B), then B is the `primary_id` and A is in `duplicate_ids`. Group all
duplicates by their referenced primary.

- Include primary records in counts, aging, and breach calculations.
- Report duplicate clusters but do NOT count duplicates as primary work.
- If a primary record itself is not in the scoped population, still report the cluster
  but exclude it from primary counts.

### 5.3 Aging Calculation
For each included primary item:
```
aging_days = as_of_date - created_date
```
Where both dates are calendar dates (ignore time-of-day).

### 5.4 Aging Buckets
Distribute primary items into these buckets by `aging_days`:

| Bucket | Range (inclusive) |
|--------|-------------------|
| 0-3    | 0 to 3 days       |
| 4-7    | 4 to 7 days       |
| 8-14   | 8 to 14 days      |
| 15-30  | 15 to 30 days     |
| 31+    | 31 or more days   |

### 5.5 Overdue Determination
An item is overdue when its `aging_days` exceeds the SLA threshold for its category
and severity, as defined in the `/api/sla-policy` data.

If SLA policy defines thresholds per category only (not per severity), use the
category-level threshold. If thresholds vary by severity, apply the severity-specific
threshold.

### 5.6 Breach Rate
```
breach_rate = overdue_primary_count / included_primary_count
```
Round to exactly 3 decimal places. If `included_primary_count` is 0, the breach rate
is `0.000`.

### 5.7 Hotspot Identification
A hotspot is the `(team, owner)` pair with the highest count of overdue primary items.

- If multiple pairs tie for the highest count, select the one that is alphabetically
  first by team, then alphabetically first by owner.
- When `owner` is null, missing, or empty, use the sentinel `UNASSIGNED` as the owner
  name.
- Count unassigned items per team separately from assigned items.

### 5.8 Missing Owner Tracking
List all included primary IDs where `owner` is null, missing, or empty. Sort
lexicographically.

### 5.9 Escalation Queue (train_005 variant)
When the template includes an escalation queue, order overdue primary IDs by:

1. Severity descending (S1 first, S4 last)
2. Within the same severity, aging days descending (oldest first)
3. Within same severity and aging, ID ascending

### 5.10 Severity Overdue Counts (train_005 variant)
Count overdue primary items grouped by severity tier (S1, S2, S3, S4). Items without a
severity are excluded from these counts.

---

## 6. Release Readiness Assessment

Applies to: train_003 pattern tasks.

### 6.1 Data Sources
Pull data from these endpoints:
- `/api/releases/{release_id}` — release metadata, milestones list, work items
- `/api/milestones` — milestone details per milestone_id
- `/api/work-items` — work item status, milestone assignment
- `/api/blockers` — blocker records linked to work items
- `/api/dependencies` — dependency edges between work items

### 6.2 Milestone Completion
For each milestone in the release (sorted by `milestone_id` ascending):

1. Identify the set of primary work items assigned to this milestone.
2. Count completed primary items (`complete_primary`) — items whose authoritative
   status is `closed` or `completed`.
3. Count total primary items (`primary_total`).
4. Compute `completion_pct = round((complete_primary / primary_total) * 100, 1)`.
   If `primary_total` is 0, `completion_pct` is `0.0`.

Do NOT use stale mirror status fields to determine completion. Use the authoritative
work item status.

### 6.3 Gating Work Items
Gating work items are non-complete (not `closed` and not `completed`) work items
associated with the release that block readiness.

Include items that:
- Are assigned to the release
- Have a non-complete authoritative status
- Are primary records (not duplicates)

Sort ascending with no duplicates.

### 6.4 Blocker Analysis
For unresolved high-impact blockers:

1. Filter blockers to those linked to the release's work items.
2. Keep only unresolved blockers (status is not `resolved` or `closed`).
3. Keep only high-impact blockers (impact field or severity indicates high/critical).
4. Group by exact `cause` text and count occurrences.
5. Report as `{ "exact cause string": count }` with no extra keys.

### 6.5 Critical Dependency Chains
A critical dependency chain is an ordered path from a blocked release work item to a
non-complete dependency:

1. Start from each blocked (has unresolved blockers) release work item.
2. Follow dependency edges: each work item may depend on another work item.
3. Build the path from the release work item through intermediate dependencies to the
   terminal non-complete dependency.
4. Each chain is an array of work item IDs `[release_wi, ..., terminal_dependency]`.
5. Sort chains lexicographically by the full path (compare arrays element by element).

### 6.6 Readiness Score
```
readiness_score = completed_primary_count / total_primary_count
```
Round to exactly 3 decimal places. Count only primary work items assigned to the
release.

### 6.7 Ship Decision
Select one of:

| Decision | Criteria |
|----------|----------|
| `SHIP` | All milestones at 100% completion, no unresolved high-impact blockers, readiness ≥ 0.95 |
| `SHIP_WITH_WATCH` | Readiness ≥ 0.70, no hard blockers, but some milestones incomplete or low-impact unresolved blockers exist |
| `NO_SHIP` | Readiness < 0.70, OR unresolved high-impact blockers present, OR critical dependency chains block progress |

When multiple criteria could apply, the most restrictive decision wins.

---

## 7. Ordering Conventions

Apply these ordering rules in every analysis:

| Subject | Order |
|---------|-------|
| Work item ID lists | Lexicographic ascending (standard string sort) |
| Team name lists | Alphabetical ascending |
| Product area lists | Alphabetical ascending |
| Category rows (tables) | Fixed order: NewFeature, TechDebt, Reliability, Security |
| Milestone rows | `milestone_id` ascending |
| Duplicate clusters | Sorted by `primary_id` ascending |
| Duplicate IDs within a cluster | Lexicographic ascending |
| Under-invested categories | Most negative gap to least negative gap |
| Gating work item IDs | Ascending with no duplicates |
| Dependency chains | Lexicographic by the full array path |
| Missing owner IDs | Lexicographic ascending |
| Overdue ID lists | Lexicographic ascending unless escalation order applies |

---

## 8. Precision Rules

| Measurement | Rounding | Applies To |
|-------------|----------|------------|
| Percentages | 1 decimal place | `completion_pct`, `actual_pct`, `target_pct`, `gap_pct` |
| Rates / ratios | 3 decimal places | `breach_rate`, `readiness_score` |
| Counts | Integer (no rounding) | All category counts, bucket counts, overdue counts |
| gap_pct | actual minus target, 1 decimal | Mix analysis |

---

## 9. Workflow

### 9.1 General Sequence
1. Read `environment_access.md` for base URL, token, and allowed endpoints.
2. Read the task prompt for scope parameters (teams, quarter, product areas, release
   ID, as-of date, categories, closed window).
3. Read the answer template (`answer_template.json`) to understand required output
   fields, enums, and constraints.
4. Fetch data from the relevant GET endpoints.
5. Use `POST /api/query` only when a structured/SQL query is needed to filter or join
   data that the GET endpoints do not directly provide.
6. Apply scoping filters, classification rules, and exclusion rules.
7. Compute metrics (percentages, gaps, rates, scores) following the precision rules.
8. Assemble the JSON answer matching the template structure exactly — no extra keys, no
   missing required keys, no prose.

### 9.2 Fetch-Then-Compute
Always fetch the full data picture before computing. Do not compute incrementally with
partial data. This avoids rework when later queries reveal records that change earlier
counts.

### 9.3 Verify Exclusion Flags
Before finalizing, verify that every excluded ID is accounted for in the appropriate
exclusion array (`excluded_duplicate_ids`, `excluded_cancelled_ids`,
`excluded_distractor_ids`). An ID should never appear in both an inclusion list and an
exclusion list.

---

## 10. Edge Cases and Defensive Rules

### 10.1 Empty Populations
- If no work items match the scope: return zero counts, empty ID arrays, `0.0` for
  percentages, `0.000` for rates.
- If a milestone has zero primary items: `completion_pct = 0.0`.

### 10.2 Missing Data
- Missing `owner` → treat as `UNASSIGNED` for hotspot and missing-owner reporting.
- Missing `severity` → exclude from severity-specific counts.
- Missing `closed_at` → exclude from closed-work analysis.
- Missing `created_at` → exclude from aging calculations.

### 10.3 Circular Dependencies
If a dependency chain contains a cycle, break the chain at the first repeated ID and
report the acyclic prefix.

### 10.4 API Error Resilience
If an endpoint returns an error or empty response, note it and proceed with whatever
data is available from other endpoints. Do not fabricate data. If critical data is
missing and the analysis cannot proceed, report the issue through the appropriate
exclusion or data-quality mechanism.

### 10.5 Duplicate of Non-Primary
If a duplicate item references a primary that is itself a duplicate, resolve the chain
to the ultimate primary. Report the cluster under the ultimate primary's ID.

---

## 11. Template Compliance Checklist

Before returning the answer, verify:

- [ ] All `required` fields from the answer template are present.
- [ ] No `additionalProperties: false` violation — no extra keys beyond the schema.
- [ ] All `const` values match exactly.
- [ ] All `enum` values are from the allowed set.
- [ ] Array lengths respect `minItems` / `maxItems`.
- [ ] ID patterns match any `pattern` regex in the schema.
- [ ] Sort orders follow Section 7 conventions.
- [ ] Numeric precision follows Section 8 rules.
- [ ] Exclusion arrays contain every excluded ID.
- [ ] No ID appears in both inclusion and exclusion lists.
