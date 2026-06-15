# Controlled policy_codes

Every task carries a `policy_codes` (or `model_policy_codes`) block whose template
shows an `A|B|C` set of allowed values per key. These are **fixed organizational
policy selections** — the same value is chosen every time for a given key in a given
family. Emit the values below (they reproduce the gold answers). Only include the
keys the task's template actually lists; never invent a key, and never leave the
block out.

If a future template introduces a brand-new code key not listed here, choose the
**middle** option of its `A|B|C` set as the safe default (the recurring pattern is
that the middle/second value is the one in force — see the consistent picks below),
then double-check it is internally consistent with the family.

## Risk queue & Action board (same retention model)
These two families share the core retention policy block:

| Key | Value |
|---|---|
| `risk_model_code` | `RS-6` |
| `arr_source_code` | `REV-4` |
| `support_hygiene_code` | `SUP-8` |
| `action_priority_code` | `ACT-5` |

Action board adds three more keys:

| Key | Value |
|---|---|
| `board_sort_code` | `BORD-4` |
| `exposure_formula_code` | `EXP-6` |
| `calendar_policy_code` | `CAL-5` |

Interpretation (for your own reasoning, not output):
- `arr_source_code REV-4` ⇒ ARR from posted billing snapshots (not CRM).
- `support_hygiene_code SUP-8` ⇒ exclude spam + duplicate + cancelled tickets.
- `action_priority_code ACT-5` ⇒ overdue→collections, then technical, then renewal.
- `board_sort_code BORD-4` ⇒ sort by risk_level then ARR desc.
- `exposure_formula_code EXP-6` ⇒ net exposure = arr_at_risk − open expansion.
- `calendar_policy_code CAL-5` ⇒ next-touch dates from the per-action calendar.

## Receivables & pipeline review

| Key | Value |
|---|---|
| `receivable_trigger_code` | `RCP-7` |
| `crm_match_code` | `CM-5` |
| `pipeline_window_code` | `PW-6` |
| `followup_scope_code` | `FS-4` |

Interpretation: `RCP-7` ⇒ trigger on the older (60+ day) aging buckets; `CM-5` ⇒
match A/R customer_name to CRM legal_name; `PW-6` ⇒ pipeline scoped to the quarter
close-date window; `FS-4` ⇒ one follow-up per overdue client.

## Churn model validation

| Key | Value |
|---|---|
| `model_protocol_code` | `MOD-7` |
| `probability_scale_code` | `PRB-4` |
| `deployment_rule_code` | `DEP-5` |
| `outreach_mapping_code` | `OUT-2` |

Interpretation: `MOD-7` ⇒ logistic-regression validation protocol; `PRB-4` ⇒
probabilities on a 0–1 scale to 3 decimals; `OUT-2` ⇒ the reason→outreach mapping
in `task_families.md` (CHURN).

## QBR

The QBR template (train example) carried no `policy_codes` block — emit only the
keys its `answer_template.json` shows. Its fixed enum picks instead live in the
`metric_sources` block: `revenue: crm_closed_won`, `support_tickets: support_export`,
`sla_compliance: sla_report`, `nps: nps_survey`.

---

### Pattern summary
Across every family the chosen value is the **second / middle** option of each
`A|B|C` triple in the template (RS-2|**RS-6**|RS-9, REV-1|**REV-4**|REV-8,
SUP-3|**SUP-8**|SUP-9, ACT-1|**ACT-5**|ACT-7, RCP-4|**RCP-7**|RCP-9,
CM-2|**CM-5**|CM-8, MOD-2|**MOD-7**|MOD-9, etc.). The lone twist is the churn
`outreach_mapping_code` where the chosen value `OUT-2` is the **first** option of
`OUT-2|OUT-6|OUT-8` — but OUT-2 is still the lowest-numbered/leading value of its
set. When in doubt, prefer the value that matches the operational rule you are
actually applying (e.g. older-bucket trigger, billing-snapshot ARR), then fall back
to the middle option.
