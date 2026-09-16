# Portfolio Category Classification Guide

## The Four Categories

| Category | Description | Common Signals |
|----------|-------------|----------------|
| `NewFeature` | Net-new user-facing or platform capabilities | Titles mentioning "add", "feature", "implement", "build"; greenfield work |
| `TechDebt` | Refactoring, modernization, cleanup of existing code | Titles mentioning "refactor", "migrate", "upgrade", "clean up", "modernize" |
| `Reliability` | Availability, performance, observability, resilience | Titles mentioning "reliability", "availability", "latency", "monitoring", "resilience", "uptime" |
| `Security` | Vulnerabilities, compliance, auth, encryption | Titles mentioning "security", "vulnerability", "CVE", "auth", "compliance", "encryption" |

## Classification Rules

1. **`portfolio_category` is authoritative.** If the work item has `portfolio_category` set to one of the four values, use it directly.

2. **Do not infer from title or labels.** If `portfolio_category` is missing or null, the item is not classifiable. Exclude it from the portfolio mix but note its existence.

3. **Do not use `legacy_category`.** It is a stale field and may disagree with the authoritative `portfolio_category`.

4. **One category per item.** Each included work item counts exactly once, under its `portfolio_category`.

## Target Mix Interpretation

Mix targets represent the desired percentage distribution of closed work across the four categories. The target values come from `/api/mix-targets` filtered by `scope_id`.

- `gap_pct = actual_pct - target_pct`
- Positive gap means over-invested relative to target.
- Negative gap means under-invested relative to target.
- The category with the largest negative gap is the primary rebalancing candidate.

## Multi-Team vs. Single-Team Mix Reviews

- **Multi-team mix**: Two teams, two product areas. Work items from either team in either product area are included if they match the quarter. The `follow_up_action` may include both `primary_category` and `secondary_category`.
- **Single-team mix**: One product area with two teams. The `recommended_action` includes a specific `owner_team` derived from the task scope.
