# HarborCRM Aquaculture Robotics Prospecting Skill

## Overview
This skill describes the standard workflow for generating a CRM-ready prospecting summary for HarborCRM's aquaculture robotics campaign, focused on the **AquaFarm Robotics Forum 2026** trade show.

## Campaign Context
- **Trade Show**: AquaFarm Robotics Forum 2026
- **Show ID**: `aquafarm_robotics_2026` (fixed value)
- **Target**: Exhibitors that make or OEM-build robotics or underwater-camera platforms
- **Policy**: Determined by the prospecting policy fetched from `/api/policies`

## API Endpoints (in dependency order)

Call these endpoints to gather all required data:

1. **`GET /api/policies`** — Fetch the prospecting policy to understand qualification rules, platform definitions, and exclusion criteria.
2. **`GET /api/tradeshows`** — Confirm the show exists and get metadata.
3. **`GET /api/tradeshows/aquafarm_robotics_2026/exhibitors`** — Get the full exhibitor list with company details, booth, country, website, platforms, and relationship type.
4. **`GET /api/tradeshows/aquafarm_robotics_2026/meeting_interest`** — Get meeting interest scores and demo request flags per exhibitor.
5. **`GET /api/crm/accounts`** — Get existing CRM accounts to detect overlap.
6. **`GET /api/crm/contacts`** — Get CRM contacts for additional overlap detection if needed.

> **Rule**: Only query endpoints and entity IDs explicitly named in the task prompt. Do not call global list/index endpoints to discover unrelated events, shows, batches, or tasks.

## Qualification Logic

### Qualified Leads
An exhibitor is **qualified** if it:
- Makes or OEM-builds robotics or underwater-camera platforms **AND**
- Is covered by the prospecting policy (check policy rules against exhibitor metadata).

Qualified leads are assigned `crm_action`: `create_account` (if not in CRM) or `update_existing` (if already in CRM).

### Excluded Exhibitors
An exhibitor is **excluded** if it falls into one of these relationship types:
- `distributor` → exclusion_reason: `distributor_only`
- `service_provider` → exclusion_reason: `service_only`
- `sensor_vendor` → exclusion_reason: `sensor_only`
- `research` → exclusion_reason: `research_only`

Excluded exhibitors always get `crm_action`: `no_import`.

## Ranking Rules (strict order)

Rank qualified leads using this **exact priority order**:

1. **Demo request** (`requested_demo` = true) first — all demo-requested leads rank above non-demo-requested leads.
2. **Meeting interest score** descending — higher scores rank higher.
3. **Broader platform coverage** — more platforms covered ranks higher (count of distinct platforms).
4. **Company name** ascending — alphabetical tie-breaker.

Assign ranks as **1-based contiguous integers** (no gaps).

## Priority Tier & Opportunity Sizing

| Priority Tier | Criteria | Opportunity Estimate (USD) |
|---------------|----------|---------------------------|
| `A` | Demo-requested AND interest score ≥ 90 | 120,000 |
| `B` | Demo-requested AND interest score ≥ 80 | 90,000 |
| `C` | All other qualified leads | 50,000 |

> **Important**: The score thresholds apply only to demo-requested leads. A non-demo-requested lead with score 95 still gets tier `C`.

## Output Schema

Produce a JSON object with these top-level keys:

```json
{
  "show_id": "aquafarm_robotics_2026",
  "summary": { ... },
  "ranked_leads": [ ... ],
  "excluded_exhibitors": [ ... ]
}
```

### Summary Object

```json
{
  "qualified_lead_count": <int>,
  "excluded_count": <int>,
  "existing_crm_overlap_count": <int>,
  "existing_crm_overlap_account_ids": [<string>, ...],
  "total_estimated_opportunity_usd": <int>,
  "platform_coverage_counts": {
    "AUV": <int>,
    "ROV": <int>,
    "Underwater Camera": <int>
  }
}
```

- `existing_crm_overlap_account_ids`: List of CRM account IDs for qualified leads that already exist in CRM. **Sort ascending**.
- `platform_coverage_counts`: Count how many **qualified leads** (not excluded) cover each platform.
- `total_estimated_opportunity_usd`: Sum of `opportunity_estimate_usd` across all ranked leads.

### Ranked Lead Object

```json
{
  "rank": <int>,
  "company_id": <string>,
  "company_name": <string>,
  "booth": <string>,
  "country": <string>,
  "website": <string>,
  "platforms": ["AUV", "ROV", "Underwater Camera"],
  "crm_account_id": <string or null>,
  "crm_action": "create_account" | "update_existing" | "no_import",
  "requested_demo": <boolean>,
  "interest_score": <int>,
  "priority_tier": "A" | "B" | "C",
  "opportunity_estimate_usd": <int>
}
```

- `platforms`: List of platforms the exhibitor covers. **Order**: AUV, ROV, Underwater Camera.
- `crm_account_id`: The existing CRM account ID if found, otherwise `null`.
- `crm_action`: `update_existing` if `crm_account_id` is not null, else `create_account`.

### Excluded Exhibitor Object

```json
{
  "company_id": <string>,
  "company_name": <string>,
  "relationship_type": "distributor" | "service_provider" | "sensor_vendor" | "research",
  "exclusion_reason": "distributor_only" | "service_only" | "sensor_only" | "research_only",
  "crm_action": "no_import"
}
```

- **Sort excluded exhibitors by `company_name` ascending**.

## Common Pitfalls

1. **Do not skip the policy check** — Always fetch `/api/policies` first; qualification rules may include nuances beyond simple platform matching.
2. **CRM overlap detection** — Match exhibitors to CRM accounts by company name or website normalization. Be careful with case sensitivity and URL prefixes (http vs https, www vs non-www).
3. **Platform ordering** — The `platforms` array must be in the exact order: AUV, ROV, Underwater Camera.
4. **Rank contiguity** — Ranks must be 1-based with no gaps, even if some qualified leads are filtered out during processing.
5. **Opportunity sum** — Only sum opportunity estimates for **ranked leads** (qualified exhibitors), not excluded ones.
6. **Platform coverage counts** — Count only qualified leads, not excluded exhibitors.
7. **Tier assignment** — A lead must have `requested_demo: true` **AND** meet the score threshold to get tier A or B. Score alone is insufficient.
8. **Excluded exhibitors visibility** — Always include excluded exhibitors in the `excluded_exhibitors` array; do not drop them silently.
9. **Show ID** — Hardcode `aquafarm_robotics_2026`; do not derive it from data.

## Workflow Summary

1. Fetch policy → understand rules.
2. Fetch exhibitors and meeting interest data.
3. Fetch CRM accounts to detect overlaps.
4. Classify each exhibitor as qualified or excluded using policy rules.
5. For qualified leads: detect CRM overlap, assign tier/opportunity, sort by ranking rules, assign contiguous ranks.
6. For excluded exhibitors: assign relationship_type, exclusion_reason, crm_action=no_import, sort by company name.
7. Compute summary aggregates (counts, overlap IDs sorted, total opportunity, platform coverage counts).
8. Assemble final JSON with exact schema structure.
