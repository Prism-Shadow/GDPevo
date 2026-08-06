# Endpoint Reference and Data-Fetch Workflow

## Endpoint → Task Archetype Map

| Endpoint | Contractor Batch | Liquor Staff Pkg | Renewal Queue |
|---|:---:|:---:|:---:|
| GET /api/policies | ✓ | ✓ | ✓ |
| GET /api/contractor/applications | ✓ | | |
| GET /api/contractor/bonds | ✓ | | |
| GET /api/contractor/insurance | ✓ | | |
| GET /api/contractor/license-history | ✓ | | |
| GET /api/contractor/violations | ✓ | | |
| GET /api/contractor/correspondence | ✓ | | |
| GET /api/contractor/inspections | ✓ | | |
| GET /api/liquor/applications | | ✓ | |
| GET /api/liquor/settlements | | ✓ | |
| GET /api/liquor/privileges | | ✓ | |
| GET /api/liquor/incidents | | ✓ | |
| GET /api/liquor/site-evidence | | ✓ | |
| GET /api/alcohol/licensees | | | ✓ |
| GET /api/alcohol/violations | | | ✓ |
| GET /api/renewal/rules | | | ✓ |
| POST /api/sql | ✓ | ✓ | ✓ |

## Standard Data-Fetch Workflow

```
1. Read environment_access.md → extract base_url and auth header.
2. Identify task archetype from prompt keywords and target IDs.
3. GET /api/policies → store current policy baseline.
4. Fetch all data endpoints listed in the prompt (parallel GET requests).
5. If cross-referencing is needed, POST /api/sql with auth header.
6. Apply archetype-specific decision rules (see SKILL.md).
7. Read input/payloads/answer_template.json for allowed enums and ordering.
8. Build JSON output, validate against template constraints.
9. Emit JSON only.
```

## Authentication

POST /api/sql requires the header specified in environment_access.md.
The header name and token value are task-run-specific — always re-read environment_access.md at execution time.
GET endpoints do not require authentication headers.

## Policy Baseline Comparison Method

1. From /api/policies, identify the "current" policy version and the "prior" version.
2. For each application, check whether the current version introduces a stricter requirement in any of:
   - Minimum bond amount
   - Minimum insurance coverage
   - Required endorsements
   - Experience hour thresholds
   - Inspection documentation standards
3. If the current version would create a deficiency that the prior version would not, set `policy_impacted: true`.
4. This applies across all three task archetypes (contractor, liquor, renewal).
