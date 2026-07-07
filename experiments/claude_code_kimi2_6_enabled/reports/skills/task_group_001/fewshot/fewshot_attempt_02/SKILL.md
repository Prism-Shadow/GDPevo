# HarborCRM Trade-Show Pipeline Skill

Reusable workflow guidance for processing marine-robotics trade-show exhibitor data through HarborCRM.

---

## 1. Task Taxonomy

The pipeline generally follows one of four patterns. Read the prompt carefully to identify which schema to produce:

| Pattern | Top-level keys | Typical endpoints used |
|---|---|---|
| **A. Qualification** | `show_id`, `campaign`, `qualified_exhibitors`, `excluded_near_misses`, `aggregate_counts` | `/shows/{id}/exhibitors`, `/exhibitors/{id}`, `/relationships`, `/enrichment/vendors/{id}`, `/campaigns/{id}/eligibility` |
| **B. CRM Import** | `show_id`, `crm_import_report` | same as A + `/crm/accounts` (search by website/domain) |
| **C. CSV Report** | flat CSV file | same as A |
| **D. Lead Ranking / Prospecting** | `show_id`, `summary`, `ranked_leads`, `excluded_exhibitors` | all of the above |

---

## 2. API Query Habits

- **Always start** with `GET /api/v1/shows/{show_id}/exhibitors` to get the raw list.
- **Iterate per exhibitor** with `GET /api/v1/exhibitors/{exhibitor_id}` for booth, country, website, product lines, etc.
- **Fetch relationships** with `GET /api/v1/relationships?entity=exhibitor&entity_id={exhibitor_id}` to determine `relationship_type` (manufacturer, distributor, service_provider, sensor_vendor, research).
- **Enrichment** via `GET /api/v1/enrichment/vendors/{vendor_id}` when a `vendor_id` is present to discover platforms and sensor capabilities.
- **Campaign eligibility** via `GET /api/v1/campaigns/{campaign_id}/eligibility` to confirm qualification rules for the specific campaign.
- **CRM deduplication** via `GET /api/v1/crm/accounts` (search by website domain) when producing import or prospecting outputs.

> Only query endpoints and entity IDs explicitly named in the prompt. Do not call global list/index endpoints to discover extra shows, campaigns, or batches.

---

## 3. Business Rules for Qualification

### 3.1 Priority Tiers
| Tier | Rule |
|---|---|
| **A** | `manufacturer` + sells platforms (AUV/ROV/Underwater Camera) + produces the campaign-specific sensor (e.g., dissolved oxygen sensors) |
| **B** | `manufacturer` + sells platforms, but does **not** produce the campaign-specific sensor |
| **C** | `manufacturer` only — no platform products |
| **Excluded** | Distributors, service providers, sensor-only vendors, research-only |

### 3.2 Platform Normalization
- Normalize whatever strings appear in `product_lines` / `platform_tags` to the canonical set: **AUV, ROV, Underwater Camera**.
- Platform arrays in JSON outputs must be ordered: **`["AUV", "ROV", "Underwater Camera"]`** (omit any the exhibitor does not have).
- In CSV outputs, platforms are **pipe-separated** in the same order: `AUV|ROV`, `ROV|Underwater Camera`, etc.

### 3.3 Exclusion Reasons
Use these exact strings:
- `distributor_only`
- `service_only`
- `sensor_vendor_only` (qualification tasks) or `sensor_only` (prospecting tasks — follow the answer template enum)
- `research_only`

---

## 4. Output Conventions & Schemas

### 4.1 Qualification Output (Pattern A)
```json
{
  "show_id": "<exact_show_id>",
  "campaign": "<campaign_id_from_prompt>",
  "qualified_exhibitors": [ ... ],
  "excluded_near_misses": [ ... ],
  "aggregate_counts": { ... }
}
```
- `qualified_exhibitors` objects contain: `company_id`, `company_name`, `platforms`, `priority_tier`, `booth`, `country`, `website`.
- `excluded_near_misses` objects contain: `company_id`, `company_name`, `exclusion_reason`.
- `aggregate_counts` must include **all** expected keys even when zero:
  - `qualified_total`
  - `platform_counts`: `{ "AUV": N, "ROV": N, "Underwater Camera": N }`
  - `priority_counts`: `{ "A": N, "B": N, "C": N }`
  - `excluded_near_misses_total`

### 4.2 CRM Import Output (Pattern B)
```json
{
  "show_id": "<exact_show_id>",
  "crm_import_report": [ ... ]
}
```
- Each entry: `company_id`, `company_name`, `crm_account_id` (string or `null`), `crm_action`, `status`, `match_basis` (string or `null`).
- `match_basis` for website matches should contain the matched domain.
- Report covers **all** exhibitors (qualified + excluded), sorted by `company_id` ascending.
- Excluded exhibitors receive `"crm_action": "no_import"`.

### 4.3 CSV Report (Pattern C)
- Columns (exact order): `Company Name`, `Country`, `Priority Tier`, `Booth`, `Platforms`, `Interest Score`
- Header row is required.
- `show_name` in the filename/prompt context should be the **human-readable show name** (not the `show_id`).
- Only **qualified** exhibitors appear.

### 4.4 Lead Ranking / Prospecting Output (Pattern D)
```json
{
  "show_id": "<exact_show_id>",
  "summary": { ... },
  "ranked_leads": [ ... ],
  "excluded_exhibitors": [ ... ]
}
```
- `summary` contains:
  - `qualified_lead_count`, `excluded_count`
  - `existing_crm_overlap_count`, `existing_crm_overlap_account_ids` (sorted ascending)
  - `total_estimated_opportunity_usd`
  - `platform_coverage_counts`: count every platform occurrence across all qualified leads (e.g., a company with ROV + Underwater Camera contributes 1 to each).
- `ranked_leads` entries include all qualified exhibitor fields plus `rank`, `crm_account_id`, `crm_action`, `requested_demo`, `interest_score`, `priority_tier`, `opportunity_estimate_usd`.
- `excluded_exhibitors` entries include `company_id`, `company_name`, `relationship_type`, `exclusion_reason`, `crm_action`.

---

## 5. Ordering Rules

Apply these sort orders consistently:

| Collection | Sort Key | Direction |
|---|---|---|
| `qualified_exhibitors` | `company_id` | ascending |
| `excluded_near_misses` | `company_id` | ascending |
| `crm_import_report` | `company_id` | ascending |
| `ranked_leads` | `rank` (1-based contiguous) | ascending |
| `excluded_exhibitors` (prospecting) | `company_name` | ascending |
| `existing_crm_overlap_account_ids` | account id | ascending |
| **CSV rows** | `Priority Tier` asc, then `Interest Score` desc, then `Company Name` asc | — |
| **Lead ranking** | `interest_score` desc, then `priority_tier` (A > B > C), then `company_name` asc | — |

---

## 6. CRM Action Rules

| Situation | `crm_action` |
|---|---|
| New qualified lead, no CRM match | `create_account` |
| Qualified lead, existing CRM account matched by website domain | `update_existing` |
| Excluded exhibitor (any reason) | `no_import` |
| Contact suppressed / duplicate / unusable (contact-cleaning tasks) | `suppress` or `no_import` per template enum |

---

## 7. Common Pitfalls

1. **Wrong show name in CSV** — use the human-readable show name for filenames/context, but the machine `show_id` in JSON `show_id` fields.
2. **Missing zero counts** — `platform_counts` and `priority_counts` must explicitly include every expected key with `0` when empty.
3. **Platform ordering** — JSON arrays and CSV pipe-strings must follow `AUV → ROV → Underwater Camera`.
4. **Exclusion reason vocabulary** — `sensor_vendor_only` vs `sensor_only` differ by task type; match the template enum exactly.
5. **Rank contiguity** — `rank` in `ranked_leads` must be 1-based and contiguous (1, 2, 3, …) with no gaps.
6. **Not deduplicating CRM** — always check `/crm/accounts` by website domain before deciding `create_account` vs `update_existing`.
7. **Over-querying** — never call global list endpoints to discover IDs; only use IDs explicitly provided in the prompt.
8. **Answer template mismatch** — if the on-disk `answer_template.json` does not match the prompt, trust the **prompt description and the solved `output/answer.json`** as the ground-truth schema.
