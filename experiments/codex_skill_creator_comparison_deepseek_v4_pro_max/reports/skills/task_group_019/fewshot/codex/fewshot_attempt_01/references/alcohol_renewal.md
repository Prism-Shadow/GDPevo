# Alcohol License Renewal Manual-Review Queue

## Endpoint Catalog

| Endpoint | Returns | Key Fields |
|---|---|---|
| `GET /api/alcohol/licensees` | Licensee records | `license_no`, `facility_name`, `address`, license class, renewal status |
| `GET /api/alcohol/violations` | Violation records | `violation_id`, `license_no` or related identifier, violation date, type, severity, status |
| `GET /api/renewal/rules` | Renewal rules | Boundary date rules, violation matching criteria, risk classification thresholds, queue size rules |
| `POST /api/sql` | SQL queries | Requires `X-Task-Token` header |

## Queue Construction Rules

### Step 1: Pull All Records

GET all licensees, violations, and renewal rules in parallel. Optionally use POST `/api/sql` to cross-reference licensees against violations or to filter by date.

### Step 2: Apply the Boundary Date

The prompt provides a boundary date (e.g., `2025-04-10`). Filter violations to only those with `violation_date` on or before the boundary date. Exclude violations with dates after the boundary — list these in `post_boundary_violation_ids_excluded` in the summary, sorted by violation_id ascending.

### Step 3: Match Violations to Licensees

Match violations to licensees using:

1. **Exact match**: Violation's `license_no` field matches a target `license_no` exactly.
2. **Close address match**: Violation record references the same facility/address as a target licensee but under a different or legacy license number. Check address fields, facility names, or legacy identifiers.
3. **Uncertain match**: Partial match where the relationship is plausible but not confirmed by address or identifier.

Set `match_confidence` accordingly: `exact`, `close_address`, or `uncertain`.

### Step 4: Count and Date Violations

For each matched licensee:
- `violation_count`: Number of pre-boundary matched violations.
- `most_recent_violation_date`: The latest `violation_date` among matched violations.
- `matched_violation_ids`: List of matched violation IDs, sorted by violation date ascending, then violation_id ascending.

### Step 5: Rank the Queue

Read renewal rules for ranking criteria. Rank by descending priority:

1. **Primary**: Violations with board-review or high-severity classification rank highest.
2. **Secondary**: Higher violation count ranks above lower count.
3. **Tertiary**: More recent `most_recent_violation_date` ranks above older.
4. **Quaternary**: Exact matches rank above close/uncertain matches.
5. **Quinary**: For ties, lower `license_no` ranks first.

Ranks must be integers 1 through the target queue size with no gaps.

### Step 6: Assign Risk Tier

- **high**: Violations include serious/board-review types, or violation count is at or above the renewal rules' high threshold, or match includes close/uncertain with serious violations.
- **medium**: Violations present but below the high threshold and no serious classifications.
- **low**: No matched violations or only minor/administrative violations well below thresholds.

### Step 7: Assign Next-Step Labels

From the template's allowed values:

- **board_review**: High-risk with serious violations or close/uncertain matches needing board attention.
- **manual_fine_check**: Licensees with violation counts suggesting fines need manual verification.
- **manual_ALERT_check**: Licensees with recent violations near the boundary date needing alert-system checks.
- **additional_record_check**: Licensees with uncertain matches or incomplete records.

### Summary Construction

- `queue_size`: Integer matching the number of queue entries.
- `boundary_date`: The boundary date from the prompt in YYYY-MM-DD.
- `post_boundary_violation_ids_excluded`: All violation IDs with dates after the boundary, sorted ascending.
- `close_or_uncertain_match_license_numbers`: License numbers with close_address or uncertain match_confidence, sorted ascending.
- `board_review_license_numbers`: License numbers with next_step_label `board_review`, sorted ascending.
