# Portfolio Work-Item Analysis Skill

Perform structured portfolio analysis against a shared API environment — mix reviews, SLA aging audits, and release-readiness assessments — using work items, targets, SLA policies, releases, milestones, blockers, and dependencies.

## Environment

The task environment provides a base URL (`<TASK_ENV_BASE_URL>`) with endpoints and credentials documented in `environment_access.md`. That file lists:

- The base URL for all API calls.
- An optional `X-Env-Token` header (name and value) required for `POST /api/query` (SQL endpoint).
- The set of allowed endpoints.

**Endpoint catalog** (availability varies per task):

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/work-items` | List all work items |
| GET | `/api/work-items/{item_id}` | Single work item detail |
| GET | `/api/mix-targets` | Target category mix percentages per scope |
| GET | `/api/sla-policy` | SLA policy definitions |
| GET | `/api/releases` | List releases |
| GET | `/api/releases/{release_id}` | Single release detail |
| GET | `/api/milestones` | Milestones for a release |
| GET | `/api/dependencies` | Work-item dependency graph |
| GET | `/api/blockers` | Blockers on work items |
| POST | `/api/query` | Restricted SQL query (requires auth header) |

Always fetch the environment data fresh — do not assume cached values. Use only the endpoints listed in `environment_access.md`.

## Data Integrity Rules

### Primary vs. Duplicate Records

Work items can appear multiple times. For every scope, identify and use exactly one **primary** (canonical) record per logical work item:

- If a work item has a `duplicate_of` field pointing to another item ID, it is a **duplicate** — exclude it from primary counts and list it in the duplicate cluster for the target primary.
- If multiple records share the same logical identity but none points to another, treat the one with the earliest `created_at` (or the one referenced by others) as primary.
- Group duplicates into **duplicate clusters**: each cluster has a `primary_id` and a sorted list of `duplicate_ids`.

### Stale Mirror Fields

Never trust mirror, export, or computed snapshot fields that may be out of date. Always read authoritative source fields:

- For release status: use the live release API, not a mirrored `release_status` on a work item.
- For work item state: use the work item's own status/state field, not a denormalized copy on a parent object.
- For category classification: use the work item's primary category field; if that is missing or ambiguous, fall back to labels and title signals in that order.

### Cancelled and Distractor Records

- **Cancelled** items in scope are excluded from the primary working set. Report them in the exclusion list.
- **Distractor** records appear to match the scope (same quarter, teams, or product area) but are not primary closed portfolio work — exclude them from counts and list them separately.

## Portfolio Categories

All work items are classified into exactly one of four categories:

| Category | Description |
|----------|-------------|
| `NewFeature` | New feature development, enhancements, user-facing additions |
| `TechDebt` | Technical debt reduction, refactoring, code quality, tooling |
| `Reliability` | Availability, performance, incident response, monitoring, resilience |
| `Security` | Vulnerabilities, auth/authz, encryption, compliance, threat mitigation |

Classification priority when signals conflict:
1. The work item's explicit `portfolio_category` or `type` field.
2. The work item's `labels` or `tags`.
3. Keywords in the work item's `title`.

If still ambiguous after all three signals, classify as `TechDebt`.

## Ordering Conventions

Apply these stable orderings consistently:

| Entity | Order |
|--------|-------|
| Work item ID lists | Lexicographically ascending (string sort) |
| Team names | Alphabetically ascending |
| Category rows in tables | Fixed order: `NewFeature`, `TechDebt`, `Reliability`, `Security` |
| Included work items | `closed_at` ascending, then ID ascending |
| Duplicate clusters | By `primary_id` lexicographically |
| IDs within a duplicate cluster | Lexicographically ascending |
| Milestone completion rows | By `milestone_id` ascending |
| Dependency chains | Lexicographically by the full path (joined with `→` or equivalent) |
| Under-invested categories | Most negative gap to least negative gap |
| Escalation queue | By severity descending (S1 before S2, etc.), then by age descending (oldest first) |

## Precision Standards

| Metric | Precision | Example |
|--------|-----------|---------|
| Percentages (completion, mix shares, gaps) | 1 decimal place | `42.5` |
| Rates and scores (breach rate, readiness score) | 3 decimal places | `0.167` |
| Counts | Integer | `12` |

Round using standard rounding (half-up). Do not round intermediate values — only round the final reported value.

## Calculation Patterns

### Mix Gap Analysis

For each category:
- `actual_pct = (category_count / total_included) × 100`, rounded to 1 decimal place.
- `gap_pct = actual_pct − target_pct`, rounded to 1 decimal place.
- A negative gap means under-investment.
- The category with the most negative gap is the largest deficit.

### SLA Aging

- **Overdue**: a primary work item whose `age_days` (from creation or SLA start to the as-of date) exceeds its SLA target. The SLA target is determined by the item's severity and category from the SLA policy data.
- **Aging buckets**: Count items by days since SLA start into buckets: `0–3`, `4–7`, `8–14`, `15–30`, `31+`.
- **Breach rate**: `overdue_primary_count ÷ included_primary_count`, rounded to 3 decimal places.

### Release Readiness

- **Ship decision**: Based on milestone completion, unresolved high-impact blockers, and critical dependencies.
  - `SHIP`: all milestones at ≥ threshold, zero unresolved high-impact blockers, no critical dependency gaps.
  - `SHIP_WITH_WATCH`: minor gaps exist but are manageable with monitoring.
  - `NO_SHIP`: significant blockers, incomplete milestones, or broken dependency chains.
- **Readiness score**: `completed_primary_work ÷ total_primary_work`, rounded to 3 decimal places.
- **Gating work items**: non-complete primary work items that block readiness (sorted, unique).
- **Critical dependency chains**: ordered paths from a blocked release work item through dependencies to a non-complete dependency.

### Hotspot Analysis (SLA)

- For each team, count overdue primary records.
- The top hotspot is the `(team, owner)` pair with the highest overdue count. If an owner is missing, report `UNASSIGNED`.
- Ties go to the first team alphabetically.

## Output Convention

Return a single JSON object matching the supplied `answer_template.json` schema exactly:

- Do not include prose, explanations, or commentary outside the JSON.
- All required fields must be present.
- No additional properties beyond those defined in the schema.
- Use the exact enum values, field names, and structure from the template.
- Empty arrays must be `[]`, not `null` or absent.

## Workflow

1. **Read** the prompt and `answer_template.json` to understand the scope and required output shape.
2. **Read** `environment_access.md` for the base URL, allowed endpoints, and query credentials.
3. **Fetch** all relevant data from the environment endpoints — work items, targets, SLA policies, releases, milestones, blockers, dependencies as the task requires.
4. **Filter** to in-scope records using the task's scope constraints (teams, quarter, product area, release ID, as-of date, etc.).
5. **Classify** each included work item into exactly one portfolio category.
6. **Separate** primary records from duplicates, cancelled items, and distractors.
7. **Calculate** the required metrics using the formulas above.
8. **Order** all lists according to the ordering conventions.
9. **Validate** that every value matches the schema's constraints (enums, patterns, types, ranges).
10. **Return** the single JSON object — nothing else.
