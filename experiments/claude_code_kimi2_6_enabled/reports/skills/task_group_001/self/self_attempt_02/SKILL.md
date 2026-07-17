# HarborCRM Aquaculture Robotics Prospecting Skill

## Overview

This skill describes how to prepare a CRM-ready prospecting summary for HarborCRM's aquaculture robotics campaign, targeting the **AquaFarm Robotics Forum 2026** trade show (`show_id`: `aquafarm_robotics_2026`).

## Required API Endpoints

Query these endpoints in order to gather all necessary data:

1. `/api/tradeshows` — Confirm the target show exists
2. `/api/tradeshows/aquafarm_robotics_2026/exhibitors` — Get full exhibitor list with metadata
3. `/api/tradeshows/aquafarm_robotics_2026/meeting_interest` — Get interest scores and demo requests
4. `/api/crm/accounts` — Check for existing CRM accounts
5. `/api/crm/contacts` — Check for existing CRM contacts (supporting data)
6. `/api/policies` — Retrieve the prospecting policy to determine qualification rules

**Important**: Only query endpoint paths and entity IDs explicitly named in the task prompt. Do not call global list/index endpoints to discover other events, shows, batches, tasks, or IDs.

## Data Gathering Workflow

### Step 1: Fetch Policy
Call `/api/policies` first to understand the qualification criteria. The policy defines which exhibitors are "qualified" (make or OEM-build robotics or underwater-camera platforms) and which are "excluded" (distributors, service providers, sensor vendors, research institutions).

### Step 2: Fetch Exhibitors
Call `/api/tradeshows/aquafarm_robotics_2026/exhibitors` to get the full exhibitor roster. Each exhibitor should have:
- `company_id`
- `company_name`
- `booth`
- `country`
- `website`
- `platforms` (list of platform types)
- `relationship_type` (e.g., manufacturer, distributor, service_provider, etc.)

### Step 3: Fetch Meeting Interest
Call `/api/tradeshows/aquafarm_robotics_2026/meeting_interest` to get:
- `interest_score` (numeric, typically 0–100)
- `requested_demo` (boolean)

Merge this data with the exhibitor list by `company_id`.

### Step 4: Check CRM Overlap
Call `/api/crm/accounts` to identify which exhibitors already exist in CRM. Match by company name or other identifying fields. For existing accounts, capture the `crm_account_id`.

## Qualification Logic

### Qualified Leads
An exhibitor is **qualified** if it:
- Makes or OEM-builds robotics or underwater-camera platforms, **AND**
- Is covered by the prospecting policy (i.e., not in an excluded category)

Qualified leads get `crm_action`: `create_account` (if not in CRM) or `update_existing` (if already in CRM).

### Excluded Exhibitors
An exhibitor is **excluded** if its `relationship_type` is one of:
- `distributor` → `exclusion_reason`: `distributor_only`
- `service_provider` → `exclusion_reason`: `service_only`
- `sensor_vendor` → `exclusion_reason`: `sensor_only`
- `research` → `exclusion_reason`: `research_only`

Excluded exhibitors always get `crm_action`: `no_import`.

## Ranking Rules

Rank **qualified leads** by the following criteria in order of priority:

1. **Demo request first**: `requested_demo === true` ranks higher than `false`
2. **Meeting interest score descending**: Higher scores rank higher
3. **Broader platform coverage**: More platforms covered ranks higher (count of platforms)
4. **Company name ascending**: Alphabetical tie-breaker

Assign ranks as 1-based contiguous integers (1, 2, 3, ...).

## Opportunity Sizing

Assign priority tier and opportunity estimate based on demo request and interest score:

| Priority Tier | Condition | Opportunity Estimate (USD) |
|---------------|-----------|---------------------------|
| `A` | `requested_demo === true` AND `interest_score >= 90` | 120,000 |
| `B` | `requested_demo === true` AND `interest_score >= 80` | 90,000 |
| `C` | All other qualified leads | 50,000 |

**Note**: The `B` tier requires `requested_demo === true`. If demo is requested but score is < 80, it falls to `C`.

## Output Schema

Produce a JSON object with these exact top-level keys:

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
  "qualified_lead_count": <integer>,
  "excluded_count": <integer>,
  "existing_crm_overlap_count": <integer>,
  "existing_crm_overlap_account_ids": [<sorted CRM account IDs ascending>],
  "total_estimated_opportunity_usd": <integer>,
  "platform_coverage_counts": {
    "AUV": <integer>,
    "ROV": <integer>,
    "Underwater Camera": <integer>
  }
}
```

- `total_estimated_opportunity_usd`: Sum of `opportunity_estimate_usd` across all ranked leads
- `platform_coverage_counts`: Count how many ranked leads cover each platform type

### Ranked Lead Object

```json
{
  "rank": <integer>,
  "company_id": <string>,
  "company_name": <string>,
  "booth": <string>,
  "country": <string>,
  "website": <string>,
  "platforms": ["AUV", "ROV", "Underwater Camera"],
  "crm_account_id": <string or null>,
  "crm_action": "create_account" | "update_existing" | "no_import",
  "requested_demo": <boolean>,
  "interest_score": <integer>,
  "priority_tier": "A" | "B" | "C",
  "opportunity_estimate_usd": <integer>
}
```

- `platforms`: Ordered exactly as `AUV`, `ROV`, `Underwater Camera`; include only platforms the exhibitor actually covers
- `crm_account_id`: The existing CRM account ID if found, otherwise `null`
- `crm_action`: `create_account` for qualified leads not in CRM, `update_existing` for qualified leads already in CRM, `no_import` for excluded exhibitors

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

- Ordering: `excluded_exhibitors` sorted by `company_name` ascending

## Common Pitfalls

1. **Do not call global list endpoints** to discover IDs. Only use the explicitly named endpoints and IDs in the prompt.
2. **Platform ordering matters**: The `platforms` array must be ordered `AUV`, `ROV`, `Underwater Camera` — not arbitrary.
3. **CRM overlap account IDs must be sorted ascending** in the summary.
4. **Excluded exhibitors must still appear** in the output under `excluded_exhibitors`, not be silently dropped.
5. **Priority tier B requires both demo requested AND score ≥ 80**. A demo request with score 79 is tier C.
6. **Rank must be contiguous** (1, 2, 3, ... with no gaps).
7. **Opportunity sizing only applies to qualified leads**. Excluded exhibitors do not contribute to `total_estimated_opportunity_usd`.
8. **Match CRM accounts carefully**: Use company name or other stable identifiers; do not create false positives.
9. **Always read the policy first**: The `/api/policies` response may contain nuanced rules about what qualifies as a robotics or underwater-camera platform.
