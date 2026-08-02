# Metrics & action plan — computation rules

## Golden rule for metrics

Metrics are computed from your **selected material set**, not the raw tables, and
**each key's own description in the template is authoritative**. Read the
description, then count. Below are the recurring definitions and the arithmetic
that keeps them consistent.

### Universally recurring
- `*_count` of a list = number of selected items in that list.
- `unlogged = withheld_count − logged_count` (per privilege entry and in
  aggregate). This identity must hold everywhere it appears.
- `categories_with_open_*` / `categories_with_any_gap_or_loss` = the sorted,
  deduped union of category codes across all *open/material* items.
- `affected_category_count` / `unique_affected_category_count` = length of that
  union.
- `nonready_category_count` / `categories_with_open_gaps` = number of categories
  carrying a material non-complete status.
- A `production_ready` / `rolling_production_ready` boolean = `false` if any open
  material gap remains; `true` only when nothing is outstanding.

### Scoped counts (read the wording carefully)
- **Box counts** (`destroyed_box_count`, `destroyed_lab_archive_box_count`,
  `pre_hold_destroyed_box_count`, `post_hold_destroyed_box_count`): sum
  `volume_count` **only** over material retention events whose
  `volume_unit == "boxes"`. Split pre/post by comparing the event vs. the hold
  date (or the event's pre/post status). If the task's named destroyed source is
  not measured in boxes, the box count is `0`.
- **Privilege doc counts** described as "from selected incomplete-log blockers
  only" include *only* the incomplete-log entries you selected as blockers — not
  waivers, not over-designation, not the whole privilege log.
- **`third_party_waiver_doc_count`** = withheld docs on the selected
  third-party-waiver entry(ies).
- **`miscoded_privileged_doc_count`** = `doc_count` of the selected
  `miscoded_privilege` QC finding(s); `miscoded_responsive_doc_count` =
  `doc_count` of the selected `miscoded_nonresponsive` / `zero_claim_contradiction`
  finding(s).
- **Source counts** (`uncollected_personal_source_count`,
  `lost_personal_device_count`, `uncollected_board_source_count`,
  `personal_email_gap_source_count`, `personal_phone_partial_source_count`,
  `available_archive_count`, `post_hold_loss_event_count`,
  `missing_required_record_count`): count the matching selected records; each
  source/event is 1.

Because metrics are derived, they must reconcile with the item lists: e.g. the
privilege `unlogged_privilege_docs` metric equals the `unlogged` on the selected
gap entry; `top_risk_count` equals the length of `top_risks`.

## Category rollup

For each request category that has any material issue:
- `status` — the template's category-status enum that best describes the dominant
  problem (preservation loss, collection/source gap, privilege-log gap,
  responsiveness gap, underproduced privilege corrections, archive available,
  mixed, …). If a category has multiple issue kinds, pick the most severe /
  most-encompassing status and set `production_impact` accordingly.
- `source_refs`/`issue_refs` — the sorted, deduped union of every selected record
  id touching that category (a lost source, its retention event, the QC finding,
  the doc, etc. — include all that apply).
- `recommended_action` — the action for the category's dominant issue.
- `open_issue_count` (when required) — number of distinct open material issue
  records summarized for that category.
Sort categories by `category_code` ascending; sort the id/category lists inside
each item ascending.

## Action plan construction

Synthesize a fresh, ranked plan (do not transcribe `remediation_actions`):

1. **One action per material issue or coherent group.** A single loss can spawn
   two actions (e.g. disclose + forensic recovery for a spoliated device);
   multiple docs from one QC finding collapse into one recode action whose
   `target_refs` list all their ids.
2. **`action_type`** from the defect (see `enum_crosswalks.md`).
3. **`owner`** from the action (see `enum_crosswalks.md`), chosen from the
   template's owner enum.
4. **`priority`/`priority_rank`/`rank`** by legal urgency: P0 disclosable
   post-hold/spoliation losses first, then P1 (uncollected sources, log gaps,
   waivers, recodes, privilege miscoding), then P2, then P3. Assign
   `priority_rank`/`rank` as a dense 1-based order; the template usually sorts by
   it ascending.
5. **`target_refs`** = the sorted hub ids the action addresses.
6. **`category_impacts`/`affected_categories`** = sorted union of the categories
   those targets touch.
7. **`due_days`** (only if the schema has it) by action type:

   | Action type | due_days |
   |---|---|
   | disclose_preservation_issue / disclose loss | 3 |
   | waiver_assessment_and_disclosure | 3 |
   | recode_and_produce | 5 |
   | supplement_privilege_log | 5 |
   | privilege_recode_and_log | 5 |
   | collect_personal_device | 7 |
   | search_archive / collect_archive | 10 |

   (Whole days from delivery; earlier for higher-severity variants when the
   prompt implies urgency.)

## Schematic worked examples (patterns, not answers)

These illustrate the mechanics with placeholder ids — do not emit these values;
recompute from the live matter.

- **Privilege-log gap →** entry with `issue_type=incomplete_log`,
  `withheld=W, logged=L`. Report `withheld_count=W, logged_count=L,
  unlogged_count=W−L`, category = the entry's `category_code`,
  finding/issue status = protocol-noncompliant, impact = withheld_unlogged,
  action = supplement_privilege_log, owner = privilege_team, priority P1. Metric
  `unlogged_privilege_docs = W−L`.
- **Spoliated personal device →** `custodian_sources` row `status=lost`,
  `post_hold=1`, `source_type=personal_phone`: severity critical, source_status
  lost, impact source_lost, `document_count=0`, categories = its
  `category_impacts`; two actions — disclose (outside_counsel, P0) and forensic
  recovery (ediscovery_vendor/forensics, P0). Metric `lost_personal_device_count
  += 1`.
- **Post-hold box destruction (boxes) →** retention `status=post_hold_loss`,
  `volume_unit=boxes`, `volume_count=B`: risk critical, disclose (P0),
  `post_hold_destroyed_box_count += B`, `destroyed_box_count += B`.
- **Zero-claim contradiction →** qc `zero_claim_contradiction`, `doc_count=n`,
  `source_ref` = the responsive docs: responsiveness miscode, not_produced,
  recode_and_produce (review vendor/QC, P1), `miscoded_responsive_doc_count += n`,
  and `source_refs` include both the finding id and the doc ids.
- **Available archive →** `custodian_sources` `status=available` with
  `archive_available` tag: not a loss but a remediation path — list it under the
  template's "available/retained sources" list, `availability_status
  = available_archive`, action collect/search archive, and set
  `available_archive_count += 1`.
