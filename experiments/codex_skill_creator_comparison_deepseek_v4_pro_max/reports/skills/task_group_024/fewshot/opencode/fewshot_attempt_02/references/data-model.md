## Portfolio Work Item Data Model

The environment models an engineering portfolio through work items, releases,
milestones, blockers, dependencies, mix targets, and SLA policies. This
reference describes the semantics that matter for correct analysis.

### Work Item Core Fields

| Field | Description |
|---|---|
| `id` | Unique identifier, e.g. `WI-24024-X001`. Case-sensitive. |
| `status` | Authoritative lifecycle state. Known values: `closed`, `active`, `cancelled`, `duplicate`. |
| `type` | Type label, e.g. `Story`, `Bug`, `Task`. |
| `category` | Authoritative portfolio category. One of: `NewFeature`, `TechDebt`, `Reliability`, `Security`. |
| `severity` | Severity level. Values: `S1`, `S2`, `S3`, `S4`. |
| `team` | Owning engineering team name. |
| `owner` | Assigned person. May be `null` when unassigned. |
| `product_area` | Product area name. |
| `scope_id` | Scope grouping identifier. |
| `quarter` | Fiscal quarter, e.g. `2024-Q3`. |
| `created_at` | ISO-8601 creation timestamp. |
| `closed_at` | ISO-8601 close timestamp. `null` when not closed. |
| `updated_at` | ISO-8601 last-update timestamp. |
| `duplicate_of` | When non-null, this item is a duplicate of the referenced primary item. |
| `release_id` | Release this item belongs to. |
| `milestone_id` | Milestone this item belongs to. |
| `mirror_status` | Stale mirror/export status field. **Never use this as truth.** Use `status` instead. |
| `legacy_category` | Stale category field. **Never use this as truth.** Use `category` instead. |

### Primary Work Items

A work item counts as **primary** for analysis when ALL of these hold:

1. Its `status` is not `cancelled`.
2. Its `duplicate_of` field is `null` (it is not a duplicate).
3. Its `mirror_status` is `null` or empty (it is not a stale mirror record).

Items that fail any of these checks are either duplicates, cancelled, or
distractor records and should be recorded in exclusion lists, not counted in
primary aggregates.

### Duplicate Handling

When `item.duplicate_of` is non-null:
- This item is a **duplicate** and points at the primary item.
- Do not count the duplicate in primary totals.
- Group duplicates by their `duplicate_of` value to form duplicate clusters.

### Category Classification

The authoritative portfolio category comes from the `category` field. The four
categories are:

- **NewFeature** — new capability or feature work.
- **TechDebt** — technical debt reduction, refactoring, or modernisation.
- **Reliability** — reliability, stability, or performance improvement.
- **Security** — security hardening, vulnerability remediation, or compliance.

When a work item's `category` field is missing or ambiguous and the task
mentions "portfolio category conventions for resolving conflicting type, label,
and title signals", use this priority order to determine the best category:

1. The `category` field (if present and valid).
2. The `type` field mapped as: `Bug` with security-related title → Security,
   `Bug` otherwise → Reliability, `Story` → NewFeature, `Task` → TechDebt.
3. Keyword signals in the `title` field: "security", "vuln", "CVE" → Security;
   "reliab", "stability", "perf", "incident" → Reliability; "refactor",
   "debt", "migrat" → TechDebt; "feature", "add", "support" → NewFeature.

### Portfolio Categories (Fixed Set)

Every analysis uses exactly these four categories in this canonical order:

```
NewFeature → TechDebt → Reliability → Security
```

Category tables, gap tables, and mix tables must list rows in this order.
