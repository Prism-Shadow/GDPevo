# test_004 Hidden Notes

## English

Task `test_004` belongs to `task_group_001`, sourced from scenario `SCN_001_crm_marketing_lead_capture` and its examples `E001`, `E002`, and `E003`. It implements the test brief from `scratch/task_group_design.md`: reconcile `Industrial Vision AI Forum 2027` (`event_id`: `industrial_vision_2027`) attendees, sponsors, and CRM gaps. The shared environment is HarborCRM under `task_group/task_group_001/env/`, especially `env/data/harborcrm_data.json`, `env/data/manifest.json`, and the public API served by `env/setup.sh`.

The visible task consists of `input/prompt.txt` and `input/payloads/answer_template.json`. Solvers are expected to inspect the public API endpoints for event details, sponsor orders, invoices, badges, CRM accounts, CRM contacts, campaign members, opportunities, and policies, then return JSON in the declared schema. The prompt intentionally asks for a business handoff rather than exposing the construction rules as a step list.

This task fits the CRM marketing lead-capture scenario because it combines event operations, sponsor finance, badge scanning, CRM contact hygiene, and campaign member cleanup. The key objects are sponsor packages for TerraLens Robotics, Mosaic AI Works, and Prairie Optics; invoice records for TerraLens and Mosaic; badge scans `bdg_0018` through `bdg_0023`; one stale CRM campaign member `acct_terra_lens:cont_lia_foster`; and policy metadata for sponsor status, contact normalization, and follow-up dates.

Material map:

- `GET /api/events/industrial_vision_2027` gives the event name, end date `2027-05-19`, lead amount `47000`, lead follow-up offset `6`, and sponsor follow-up offset `3`.
- `GET /api/events/industrial_vision_2027/sponsor_packages` gives the active sponsor package candidates and package amounts.
- `GET /api/finance/invoices?event_id=industrial_vision_2027` distinguishes TerraLens as `paid_deferred`, Mosaic as an open invoice, and Prairie Optics as proposal-only because no delivered invoice exists.
- `GET /api/events/industrial_vision_2027/badges` supplies attendee records and contact facts. Prairie Optics is classified as a sponsor attendee even though its badge type is `attendee`, because it appears in active sponsor package data.
- `GET /api/crm/accounts` and `GET /api/crm/contacts` show that Crown Assembly and DeltaForge Tools are new account/contact gaps, while the existing TerraLens `Lia Foster` contact is opted out and stale.
- `GET /api/crm/campaign_members?event_id=industrial_vision_2027` exposes the stale TerraLens member that should be updated to `excluded`, not reused for Victor Hale or Crown Assembly's Lia Foster.
- `GET /api/policies` records the public normalization and due-date conventions.

Solution basis:

- Sponsor statuses: Mosaic AI Works `open_invoice` for `24000`; Prairie Optics `proposal_only` for `11000`; TerraLens Robotics `paid_deferred` for `38000`.
- Badge classifications: `bdg_0018`, `bdg_0020`, and `bdg_0022` are sponsor attendees; `bdg_0019` Crown Assembly and `bdg_0021` DeltaForge Tools are qualified non-sponsor leads; `bdg_0023` West Bay University is excluded as `non_business_badge`.
- Campaign actions: create campaign members for the five actionable badge contacts and update stale subject `acct_terra_lens:cont_lia_foster` to `excluded`.
- New lead contacts: Crown Assembly / Lia Foster has normalized email `lia.foster@crownassembly.example` and phone `13135550104`; DeltaForge Tools / Noah Kim has empty normalized email and phone `12165550180`.
- Opportunity total: two qualified non-sponsor accounts at `47000` each, total `94000`.
- Sponsor follow-up: unpaid sponsor accounts are Mosaic AI Works and Prairie Optics, total `35000`.
- Due dates: lead due date is `2027-05-25`; sponsor finance due date is `2027-05-22`.
- Exclusion counts: sponsor attendee `3`, non-business badge `1`, existing disqualified `0`, missing contact `0`.

Evaluation basis: `eval/evaluate.py` has seven exact-match scoring points with raw weights `[3, 2, 2, 2, 2, 2, 1]`.

- SP001, weight 3: sponsor status set and badge sponsor/attendee classification.
- SP002, weight 2: campaign member create/update decisions, including the stale CRM gap.
- SP003, weight 2: unpaid sponsor follow-up account set and amount.
- SP004, weight 2: new lead contact normalization and CRM create decisions.
- SP005, weight 2: non-sponsor opportunity account set and total.
- SP006, weight 2: lead and sponsor follow-up due dates.
- SP007, weight 1: exclusion reason counts and CRM gap summary.

Likely model pitfalls include treating Prairie Optics as an ordinary attendee because its badge type is not `sponsor`; missing the proposal-only sponsor state; counting sponsor attendees as sales leads; suppressing Crown Assembly's Lia Foster because of a same-name stale opted-out TerraLens contact; reusing the stale TerraLens campaign member for the wrong person; and using the audit date instead of event-end-date offsets for due dates.

Transfer design: this test is anchored by `train_001`, `train_003`, and `train_004`. From `train_001`, solvers should transfer sponsor finance status handling and event-end-date follow-up conventions. From `train_004`, they should transfer sponsor attendee exclusion, campaign member action patterns, and proposal-only sponsor handling. From `train_003`, they should transfer email/phone normalization and cautious duplicate/contact matching. The task-specific exploration is identifying the fresh Industrial Vision sponsor and badge records, interpreting the TerraLens stale campaign member, and calculating the new event's amounts and dates.

Construction record: created by Codex task-builder for `test_004` on 2026-06-01. Files created: `input/prompt.txt`, `input/payloads/answer_template.json`, `notes/notes.md`, `output/answer.json`, `eval/eval.sh`, and `eval/evaluate.py`.

