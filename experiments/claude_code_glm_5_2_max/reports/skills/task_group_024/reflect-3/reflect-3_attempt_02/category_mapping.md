# Portfolio Category Mapping Reference

## Standard work_type → Category Mapping

| work_type    | Category    | Notes |
|-------------|-------------|-------|
| Feature      | NewFeature | Clear new feature work |
| Enhancement  | NewFeature | Enhancements default to NewFeature unless labels override |
| Refactor     | TechDebt   | Code restructuring |
| Chore        | TechDebt   | May map to Reliability if labels strongly signal reliability (flaky, latency) |
| Dependency   | TechDebt   | Dependency upgrades |
| Bug          | TechDebt   | Bug fixes default to TechDebt unless labels override |
| Incident     | Reliability | Incident response is Reliability |
| Reliability  | Reliability | Explicit reliability work |
| Security     | Security   | Explicit security work |
| Compliance   | Security   | Compliance maps to Security |

## Label Override Rules

When `work_type` maps to a category but the `labels` array contains strong competing signals:

1. **Enhancement + reliability/outage/latency/flaky labels** → Reliability (override from NewFeature)
2. **Chore + reliability/flaky labels** → Reliability (override from TechDebt)
3. **Bug + reliability/flaky labels** → possibly Reliability (context-dependent)

The resolution principle: conflicting label signals > work_type default. But only override when label signals are strong and unambiguous.

## Fields to IGNORE

- `mirror_status` — stale mirror/export field, not authoritative
- `legacy_category` — legacy classification, not authoritative

Always set `ignored_mirror_status_and_legacy_category: true` when the answer schema requires it.
