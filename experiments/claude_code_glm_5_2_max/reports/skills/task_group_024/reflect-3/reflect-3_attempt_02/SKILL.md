# Portfolio Environment Analysis Skill

## Purpose

Answer structured questions about an engineering portfolio environment by querying REST endpoints, resolving data conflicts, and computing precise metrics. Three task families appear:

1. **Portfolio Mix Review** — classifying closed work items into portfolio categories, comparing actual vs. target mix, identifying under-invested categories, and recommending rebalance actions.
2. **SLA Aging Audit** — identifying primary SLA-relevant work items, computing overdue counts and breach rates, building escalation queues, and reporting duplicate clusters.
3. **Release Readiness Assessment** — evaluating milestone completion, gating work items, unresolved high-impact blockers, critical dependency chains, and a ship decision.

## Environment Access

- Base URL and auth token are provided at runtime via `environment_access.md`.
- All requests use header `X-Env-Token: <token>`.
- Available endpoints:
  - `GET /api/work-items` — all work items (paginated or full list)
  - `GET /api/work-items/{item_id}` — single work item
  - `GET /api/mix-targets` — target mix percentages per scope
  - `GET /api/sla-policy` — SLA days-to-due by severity
  - `GET /api/releases` — release records
  - `GET /api/releases/{release_id}` — single release
  - `GET /api/milestones` — milestone records
  - `GET /api/dependencies` — dependency relationships
  - `GET /api/blockers` — blocker records
  - `POST /api/query` — restricted SQL query (same auth header)
- **Authoritative fields**: use `status`, `work_type`, `closed_at`, `created_at`, `due_at`, `owner`, `duplicate_of`, `milestone_id`, `release_id`, `team`, `product_area`, `severity`, `labels`, `title` directly from `/api/work-items`.
- **Stale/decoy fields**: `mirror_status` and `legacy_category` are non-authoritative mirrors or exports. Ignore them. Set `ignored_mirror_status_and_legacy_category: true` when the schema requires it.

## Portfolio Category Mapping

Map each work item's `work_type` to exactly one portfolio category:

| work_type        | Portfolio Category |
|------------------|--------------------|
| Feature          | NewFeature         |
| Enhancement      | NewFeature         |
| Refactor         | TechDebt           |
| Chore            | TechDebt           |
| Dependency       | TechDebt           |
| Bug              | TechDebt           |
| Incident         | Reliability        |
| Reliability      | Reliability        |
| Security         | Security           |
| Compliance       | Security           |

**Signal conflict resolution**: When `work_type` alone is ambiguous and `labels` contain strong competing signals (e.g., Enhancement with reliability/outage labels, or chore with flaky/reliability labels), prefer the label-driven category. The hierarchy is: conflicting label signals > work_type default. Enhancements with `reliability`/`outage`/`latency`/`flaky` labels should map to **Reliability**. Chores with `reliability`/`flaky` labels may also map to **Reliability** depending on the label strength. When in doubt, trust `work_type` as the primary signal.

## Common Data Preparation

### Filtering in-scope items
- Match `team` and `product_area` as specified in the task scope.
- For quarter-based reviews, retain only items with `closed_at` in the target quarter (e.g., `2025-10-01` to `2025-12-31` for Q4).
- Exclude **duplicates**: items where `status == "Duplicate"` OR `duplicate_of` is not null.
- Exclude **cancelled**: items where `status == "Cancelled"`.
- Excluded IDs should be reported in answer fields (`excluded_duplicate_ids`, `excluded_cancelled_ids`, `excluded_distractor_ids` as applicable).

### Sorting
- ID lists: sort lexicographically (ascending) unless otherwise specified.
- Items ordered by time: sort by `closed_at` ascending, then `id` ascending.
- Mix/gap tables: rows appear in the fixed order NewFeature, TechDebt, Reliability, Security.
- Teams and product areas: sort alphabetically unless the template specifies a fixed order.

### Rounding
- Percentages: 1 decimal place (e.g., `33.3`).
- Rates and scores: 3 decimal places (e.g., `0.273`).
- Gap = actual − target (percentage points, 1 decimal).

## Task Family 1: Portfolio Mix Review

### Steps
1. Fetch `/api/work-items` and `/api/mix-targets`.
2. Filter to in-scope items (team, product_area, quarter, non-duplicate, non-cancelled).
3. Classify each included item into a portfolio category using the mapping above.
4. Compute `category_counts` (item counts, not story points).
5. Compute `category_percentages` = `count / total * 100`, rounded to 1 decimal.
6. Look up target mix from `/api/mix-targets` using `scope_id`. Target values are fractions (e.g., `0.34` = `34.0%`).
7. Build `gap_table`: each row has `target_pct`, `actual_pct`, `gap_pct = actual_pct - target_pct`.
8. `under_invested_categories`: categories with negative `gap_pct`, sorted most-negative first.
9. `follow_up_action`:
   - If any negative gaps: `action = "REBALANCE_CAPACITY"`, `primary_category` = category with most negative gap, `rationale_code = "LARGEST_NEGATIVE_GAP"`.
   - If no negative gaps: `action = "MAINTAIN_CURRENT_MIX"`, `rationale_code = "NO_NEGATIVE_GAPS"`.
   - If contradictory data: `action = "INVESTIGATE_DATA_QUALITY"`, `rationale_code = "DATA_CONFLICT"`.
10. `exclusion_flags`: list excluded duplicate IDs and cancelled IDs. Set `ignored_mirror_status_and_legacy_category: true`.

## Task Family 2: SLA Aging Audit

### Concepts
- **Primary** = not a duplicate (no `duplicate_of`, status ≠ Duplicate) and not cancelled.
- **SLA population** = primary items in SLA categories (Reliability, Security), open on the as-of date OR closed within the recent-closed window.
- **Open on as-of date** = `closed_at` is null OR `closed_at > as_of`.
- **Recently closed** = `closed_at` within `[as_of − window_days, as_of]`.
- **As-of snapshot**: an item only counts if `created_at ≤ as_of` (it had to exist on the snapshot date).
- **SLA deadline** = `created_at + sla_days[severity]` (from `/api/sla-policy`).
- **Overdue** = SLA deadline < as_of AND item was open on as_of.
  - Recently-closed items that were overdue when closed (closed_at > sla_deadline) also count as overdue.
- **Aging** = days past SLA deadline. Bucket: 0–3, 4–7, 8–14, 15–30, 31+.
- **Breach rate** = overdue primary count / included primary count, 3 decimal places.
- **Duplicate clusters**: group by `duplicate_of`. Each cluster has `primary_id` (the canonical item) and `duplicate_ids` (sorted). Report clusters for in-scope items where the duplicate is in an SLA category.
- **Missing owner**: included primary items where `owner` is null.
- **Escalation queue**: overdue items sorted by severity (S1 first), then by days overdue descending, then by ID ascending.

### Steps
1. Fetch `/api/work-items` and `/api/sla-policy`.
2. Filter by team and SLA category (Reliability, Security).
3. Exclude duplicates and cancelled items.
4. Apply as-of snapshot filter (`created_at ≤ as_of`).
5. Include items open on as-of or recently closed.
6. Compute SLA deadline per item and determine overdue status.
7. Compute aging bucket counts.
8. Build overdue team counts and top hotspot (team + owner pair with most overdue).
9. Collect duplicate clusters from all in-scope duplicate records.
10. Compute breach rate.

## Task Family 3: Release Readiness Assessment

### Concepts
- **Release work items**: items with `release_id` matching the target release.
- **Primary**: not duplicate/cancelled and no `duplicate_of`.
- **Complete statuses**: Verified, Done, Closed, Deployed.
- **Milestone completion**: per milestone, count primary items that are complete vs. total primary items.
- **Gating items**: non-complete primary release work items.
- **High-impact unresolved blockers**: severity = High or Critical AND status ≠ Resolved.
- **Blocker cause counts**: key = exact cause string, value = count of matching high-impact unresolved blockers.
- **Critical dependency chains**: ordered path of work item IDs from a release work item to a non-complete dependency item. A dependency is "non-complete" if its status is not in the complete set. Follow transitive dependencies (BFS).
- **Readiness score** = completed primary / total primary, rounded to 3 decimal places.
- **Ship decision**:
  - `NO_SHIP` if any high-impact unresolved blockers exist.
  - `SHIP_WITH_WATCH` if readiness < 1.0 but no high-impact blockers.
  - `SHIP` if readiness = 1.0 and no unresolved blockers.

### Steps
1. Fetch `/api/releases`, `/api/milestones`, `/api/work-items`, `/api/blockers`, `/api/dependencies`.
2. Filter work items by `release_id`.
3. Compute milestone completion metrics.
4. Identify gating items (non-complete primary release items).
5. Aggregate blocker cause counts (high-impact, unresolved only).
6. Trace critical dependency chains from release work items to non-complete dependencies.
7. Compute readiness score.
8. Determine ship decision.
