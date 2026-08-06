# Portfolio category classification

Assign every **included** work item to exactly one of: `NewFeature, TechDebt, Reliability,
Security`.

## Primary rule — `work_type` is authoritative

| work_type   | category    |
|-------------|-------------|
| Feature     | NewFeature  |
| Enhancement | NewFeature  |
| Refactor    | TechDebt    |
| Chore       | TechDebt    |
| Dependency  | TechDebt    |
| Reliability | Reliability |
| Incident    | Reliability |
| Bug         | Reliability |
| Security    | Security    |
| Compliance  | Security    |

When the task says to "resolve conflicting **type, label, and title** signals," the
resolution is: **the `work_type` type signal wins.** `labels` and `title` are corroborating
noise (they frequently disagree by design), and `legacy_category` is ignored completely.
This mapping is total over the ten observed `work_type` values.

## Fallback — only when `work_type` is absent or not in the table above

Scan `labels` + `title` and pick the **highest-priority** category with any keyword hit,
priority order **Security > Reliability > TechDebt > NewFeature**. If nothing matches,
default to **NewFeature**.

Keyword sets (case-insensitive substring match):

- **Security**: `security, auth, encryption, cve, compliance, vulnerability, audit`
- **Reliability**: `reliability, flaky, outage, latency, incident, stabilize`
- **TechDebt**: `cleanup, refactor, migration, migrate, dependency, debt`
- **NewFeature**: `feature, rollout, launch, customer-request`

## Why this holds (evidence)

Each `work_type` value's dominant labels agree with the mapping above (e.g. `Bug` items are
dominated by `flaky`/`reliability`/`outage` → Reliability; `Compliance` by
`security`/`encryption`/`compliance` → Security). The environment deliberately seeds
conflicting `labels`/`title`/`legacy_category` values as distractors; anchoring on
`work_type` yields a single, deterministic category per item and percentages that sum to 100.

## Sanity checks
- Every included item classifies; no "unmapped" items remain.
- The four category counts sum to `total_included`.
- The four `actual_pct` values sum to ~100 (±0.1 rounding).
