# Classification Guide

This guide captures the classification patterns observed across the training examples. Apply these rules when classifying work items into portfolio categories.

## Category Resolution Priority

1. **Authoritative `category` field** — use it if it matches `NewFeature`, `TechDebt`, `Reliability`, or `Security`.
2. **Labels** — scan the `labels` array for a label matching one of the four categories.
3. **Title keywords** — inspect the title text.
4. **Default** — if no signal resolves, default to `TechDebt`.

## Title Keyword Mapping

### Security
Keywords: `security`, `vuln`, `vulnerability`, `cve`, `CVE`, `auth`, `authentication`, `entitlement`, `compliance`, `audit`, `penetration`, `threat`, `exploit`, `credential`, `token`, `cert`, `TLS`, `encrypt`

### Reliability
Keywords: `reliability`, `resilience`, `failover`, `availability`, `SLO`, `SLA`, `latency`, `outage`, `incident`, `recovery`, `downtime`, `circuit breaker`, `retry`, `timeout`, `degradation`, `stability`

### TechDebt
Keywords: `refactor`, `migrate`, `migration`, `upgrade`, `debt`, `cleanup`, `deprecate`, `deprecation`, `modernize`, `consolidate`, `remove`, `legacy`, `rewrite`, `restructure`

### NewFeature
Keywords: `feature`, `enable`, `launch`, `add`, `build`, `integrate`, `integration`, `new`, `support for`, `implement`, `create`, `introduce`

## Edge Cases

**Mixed signals**: When a title mentions both security and reliability concepts (e.g., "Secure failover for auth service"), the authoritative category or label takes precedence. If neither is available, the first keyword in the title wins, scanning in Security → Reliability → TechDebt → NewFeature order, on the rationale that safety/security work is more critical to classify correctly.

**Null/empty category**: Not all work items have a category field set. Do not treat a null category as `NewFeature`. Always check labels and title.

**Severity-implied classification**: Work items with severity S1-S4 are typically Security or Reliability items. However, rely on the explicit category/label/title signals rather than inferring from severity alone.

## Distractor Recognition

Records that should be excluded from primary counts:

- `status` = `cancelled`, `duplicate`, `mirror`, `superseded`
- `mirror_of` field is non-null (this is a mirror record)
- `duplicate_of` field is non-null (this is a duplicate record)
- The work item's `release_id` or `quarter` does not match the scope after checking authoritative fields

When in doubt about whether a record is a distractor, check:
1. Does it have a `mirror_of` or `duplicate_of` pointer? → exclude.
2. Is its status cancelled? → exclude.
3. Is its authoritative status not "closed" (or equivalent)? → exclude from closed-work calculations.
4. Does the primary record it mirrors already appear in the included set? → exclude the mirror, keep the primary.
