# Portfolio Classification – Worked Examples

These examples are derived from observed patterns in portfolio-management tasks.
Use them as reference when resolving conflicting work_type, label, and
legacy_category signals.

## Classification Priority

The four portfolio categories are **NewFeature**, **TechDebt**, **Reliability**,
and **Security**.

Classification follows a priority-ranked resolution: `work_type` is the
strongest signal, `labels` is second, `legacy_category` is third, and `title`
context is the tie-breaker. An unambiguous `work_type` like "Security",
"Reliability", "Incident", or "Refactor" dominates all other signals. Generic
`work_type` values ("Feature", "Enhancement", "Bug", "Chore", "Dependency")
yield to stronger label or legacy signals.

---

## Example 1: Unambiguous work_type

```json
{"work_type": "Security", "labels": "...", "legacy_category": "..."}
```
→ **Security**. `work_type: "Security"` dominates regardless of other fields.

```json
{"work_type": "Compliance", "labels": "...", "legacy_category": "..."}
```
→ **Security**. Compliance work counts as security.

```json
{"work_type": "Reliability", "labels": "...", "legacy_category": "..."}
```
→ **Reliability**.

```json
{"work_type": "Incident", "labels": "...", "legacy_category": "..."}
```
→ **Reliability**. Incident response is reliability work.

```json
{"work_type": "Refactor", "labels": "...", "legacy_category": "..."}
```
→ **TechDebt**. Refactor always maps to TechDebt, even when labels
contain security-related keywords. The refactoring nature dominates.

```json
{"work_type": "Chore", "labels": "...", "legacy_category": "..."}
```
→ Usually **TechDebt**. However, when `labels` explicitly contain "security",
"cve", or "encryption" AND the `title` describes security work (not cleanup),
classify as **Security**. Chore is a weak work_type that can be overridden.

---

## Example 2: Bug work_type – label-driven

```json
{
  "id": "WI-24024-P021",
  "work_type": "Bug",
  "labels": ["reliability", "flaky", "cleanup"],
  "legacy_category": "bug"
}
```
→ **Reliability**. Bug with reliability labels (`reliability` or `flaky`)
indicates the fix addresses a specific reliability issue.

```json
{
  "id": "WI-24024-007",
  "work_type": "Bug",
  "labels": ["flaky", "reliability"],
  "legacy_category": "quality"
}
```
→ **Reliability**. Same reasoning: `flaky` and `reliability` labels signal a
reliability bug fix.

A Bug without reliability/security labels:
```json
{
  "work_type": "Bug",
  "labels": ["ui", "cosmetic"],
  "legacy_category": "bug"
}
```
→ **TechDebt**. Ordinary defect fix.

---

## Example 3: Feature / Enhancement – label or legacy driven

```json
{
  "id": "WI-24024-P022",
  "work_type": "Feature",
  "labels": ["feature", "rollout", "auth"],
  "legacy_category": "security"
}
```
→ **Security**. `legacy_category: "security"` plus label "auth" tips a generic
Feature into Security.

```json
{
  "id": "WI-24024-P001",
  "work_type": "Feature",
  "labels": ["feature", "rollout", "security"],
  "legacy_category": "security"
}
```
→ **Security**. Explicit "security" label + security legacy.

```json
{
  "id": "WI-24024-P026",
  "work_type": "Enhancement",
  "labels": ["feature", "rollout"],
  "legacy_category": "maintenance"
}
```
→ **NewFeature**. Enhancement with generic feature/rollout labels and no
security or reliability indicator. The `maintenance` legacy alone does not
force TechDebt for an Enhancement.

```json
{
  "id": "WI-24024-P008",
  "work_type": "Enhancement",
  "labels": ["outage", "reliability", "feature"],
  "legacy_category": "new"
}
```
→ **Reliability**. Labels "outage" and "reliability" override the generic
Enhancement work_type.

```json
{
  "id": "WI-24024-P004",
  "work_type": "Feature",
  "labels": ["feature", "migration"],
  "legacy_category": "maintenance"
}
```
→ **TechDebt**. Feature with "migration" label and "maintenance" legacy
indicates this is maintenance/migration work rather than a new feature.

```json
{
  "id": "WI-24024-022",
  "work_type": "Enhancement",
  "labels": ["feature", "outage"],
  "legacy_category": "admin"
}
```
→ **Reliability**. "outage" label overrides generic Enhancement.

```json
{
  "id": "WI-24024-098",
  "work_type": "Enhancement",
  "labels": ["feature", "rollout"],
  "legacy_category": "security"
}
```
→ **Security**. `legacy_category: "security"` tips this Enhancement to
Security. Title "Cleanup rollout billing ledger writer" has "cleanup" but the
security legacy is the stronger signal.

---

## Example 4: Dependency – context-dependent

```json
{
  "id": "WI-24024-P007",
  "work_type": "Dependency",
  "labels": ["migration", "cleanup", "auth"],
  "legacy_category": "security"
}
```
→ **TechDebt**. "Dependency" work_type is a maintenance signal. The label
"auth" describes what the dependency touches, not that the work itself is
security-focused. Title "Atlas migration cleanup with auth title" reinforces
the cleanup/migration nature.

```json
{
  "id": "WI-24024-009",
  "work_type": "Dependency",
  "labels": ["auth", "migration", "security"],
  "legacy_category": "maintenance"
}
```
→ **Security**. Here "security" is explicitly in labels, and the work
("Orion auth dependency upgrade") is upgrading a security dependency. The
explicit security label wins over the generic Dependency work_type.

The distinction: when Dependency work items have explicit security labels AND
the title describes security/upgrade work (rather than cleanup), classify as
Security. When the labels are about what the dependency touches (auth,
encryption) but the title describes cleanup/migration, classify as TechDebt.

---

## Example 5: Refactor – always TechDebt

```json
{
  "id": "WI-24024-P002",
  "work_type": "Refactor",
  "labels": ["auth", "encryption", "cleanup", "refactor"],
  "legacy_category": "tech-debt"
}
```
→ **TechDebt**. Refactor dominates all other signals. Even with "auth" and
"encryption" in labels, the work is refactoring existing code.

```json
{
  "id": "WI-24024-P024",
  "work_type": "Refactor",
  "labels": ["migration", "cleanup", "feature"],
  "legacy_category": "new"
}
```
→ **TechDebt**. Refactor overrides "new" legacy.

---

## Example 6: Chore – usually TechDebt, exception for explicit security

```json
{
  "id": "WI-24024-P005",
  "work_type": "Chore",
  "labels": ["cleanup", "flaky", "reliability"],
  "legacy_category": "quality"
}
```
→ **TechDebt**. Chore is operational maintenance. The reliability labels
describe the subject of the cleanup, not proactive reliability engineering.

```json
{
  "id": "WI-24024-095",
  "work_type": "Chore",
  "labels": ["cleanup", "encryption"],
  "legacy_category": "bug"
}
```
→ **Security** for SLA contexts. The "encryption" label plus title
"Rollout encryption edge routing policy" indicates this Chore is
security-focused work. For portfolio-mix classification, this is TechDebt
(Chore dominates); for SLA filtered to Security/Reliability, the encryption
signal qualifies it as Security.

---

## Example 7: Incident – always Reliability

```json
{
  "id": "WI-24024-P025",
  "work_type": "Incident",
  "labels": ["outage", "incident", "feature"],
  "legacy_category": "new"
}
```
→ **Reliability**. Incident always maps to Reliability.

```json
{
  "id": "WI-24024-S022",
  "work_type": "Incident",
  "labels": ["auth", "outage", "reliability"],
  "legacy_category": "quality"
}
```
→ **Reliability**. Even with "auth" label, Incident dominates.

---

## Quick-Reference Table

| work_type | Default | Override by labels/legacy | Examples |
|-----------|---------|---------------------------|----------|
| Security, Compliance | Security | Never | — |
| Reliability | Reliability | Never | — |
| Incident | Reliability | Never | — |
| Refactor | TechDebt | Never | — |
| Bug | TechDebt | → Reliability if labels have reliability/flaky/outage | WI-24024-P021 |
| Chore | TechDebt | → Security if labels have security/cve/encryption + title confirms | WI-24024-095 |
| Dependency | TechDebt | → Security if labels explicitly have security + title is upgrade/work | WI-24024-009 |
| Feature, Enhancement | NewFeature | → Security/Reliability/TechDebt based on labels + legacy | WI-24024-P001 |

## Resolving Conflicts

When signals disagree, follow this priority:

1. **Unambiguous work_type** (Security, Reliability, Incident, Refactor) —
   classify directly, skip the rest.
2. **Labels** — the strongest indicator after work_type. Look for category
   keywords: `security`, `cve`, `auth`, `encryption` → Security; `reliability`,
   `outage`, `incident`, `latency`, `flaky` → Reliability; `migration`,
   `cleanup`, `refactor`, `bug` → TechDebt.
3. **Legacy category** — weaker than labels, use when labels are silent or
   generic.
4. **Title context** — read the title for confirmation. Titles describing
   "rollout", "upgrade", "audit" suggest new work; "cleanup", "migration",
   "refactor" suggest TechDebt; "outage", "incident" suggest Reliability;
   "cve", "encryption" suggest Security.

When in doubt, prefer Security/Reliability over NewFeature/TechDebt for items
with mixed signals — the security and reliability signals are usually
intentional.
