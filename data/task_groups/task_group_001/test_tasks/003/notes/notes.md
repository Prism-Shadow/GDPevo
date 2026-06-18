# test_003 Notes
## English

This task belongs to source scenario `SCN_001_crm_marketing_lead_capture`, using source examples `E001`, `E002`, and especially `E003` for CRM contact-import hygiene. It implements the task-group design brief for `test_003`: prepare the HarborCRM raw import batch `q1_partner_import` for CRM import while respecting existing CRM records and suppression. The shared environment data is in `task_group/task_group_001/env/data/harborcrm_data.json`; public solver access is through the HarborCRM API endpoints for import batches, raw contacts, suppression, CRM accounts, CRM contacts, and policies. The only task-local solver payload is `input/payloads/answer_template.json`.

The solver-visible task asks for a structured CRM-ready JSON summary, not a CRM mutation. The expected output includes batch metadata, surviving cleaned contacts, duplicate metadata, removal metadata, import action totals, and the campaign-member import count plus source label. The visible prompt is intentionally compact and does not expose the contact-hygiene SOP as a step list; solvers are expected to infer and apply the public policies and train-derived conventions.

The important source records are raw rows `q1_001` through `q1_008`. `q1_002` wins over `q1_001` for Hana Park because the normalized email matches and `q1_002` is more recent, even though its source priority is lower. `q1_008` wins over `q1_007` for Miles Chen because the normalized email matches and `q1_008` is later and comes from `badge_scan`. `q1_003` survives as an existing LakeHealth account contact with no existing contact id. `q1_004` survives as a phone-only new account. `q1_005` is unusable because it has neither normalized email nor normalized phone. `q1_006` is suppressed through the batch suppression list. Riverbend Chemical already exists as CRM account `acct_riverbend_chem`, and Hana Park matches existing contact `cont_hana_park`; LakeHealth Robotics already exists as `acct_lakehealth`, but Pia Norberg has no existing contact. DeltaForge Tools and Cascadia Steel are new account creates.

The material map is:

- `GET /api/import_batches` identifies campaign code `PARTNER-Q1-2027` and source label `partner_and_manual_upload` for `q1_partner_import`.
- `GET /api/import_batches/q1_partner_import/raw_contacts` provides rows `q1_001` through `q1_008` to normalize, suppress, dedupe, and import.
- `GET /api/import_batches/q1_partner_import/suppression` identifies the suppressed Lia Foster row via `lia.foster@crownassembly.example` and phone `13135550104`.
- `GET /api/crm/accounts` determines existing account updates for Riverbend Chemical and LakeHealth Robotics.
- `GET /api/crm/contacts` identifies `cont_hana_park` as an existing stale Riverbend contact and confirms that Pia Norberg, Noah Kim, and Miles Chen are not existing contacts.
- `GET /api/policies` exposes the normalization, source-priority, and dedupe conventions needed to resolve the batch.

The standard answer in `output/answer.json` has four clean contacts sorted by row id: `q1_002`, `q1_003`, `q1_004`, and `q1_008`. Email values are lowercase and trimmed. Phone values are digits-only from the winning row, so Hana Park's winning row has `7135550138` rather than the country-prefixed phone from the losing row. Duplicate removal count is `2`, with duplicate keys `email:hana.park@riverbendchem.example` and `email:miles.chen@cascadiasteel.example`. Removal counts are one unusable row and one suppressed row. Import action totals are `create_account: 2`, `update_existing: 2`, `no_import: 3`, and `suppress: 1`. Campaign member import is count `4` with source label `partner_and_manual_upload`.

The evaluator has six scoring points, matching the design:

- SP001, weight 3: exact ordered surviving cleaned contact IDs.
- SP002, weight 3: normalized email and phone values by survivor id.
- SP003, weight 2: duplicate resolution winners and removed row ids.
- SP004, weight 2: unusable and suppressed removal counts with the relevant removed rows.
- SP005, weight 2: create/update/no-import/suppress action totals.
- SP006, weight 1: campaign member count and source label.

Likely pitfalls include choosing the higher-priority but older `q1_001` over `q1_002`, mixing the winning Hana row's email with the losing row's phone, keeping the suppressed Lia Foster row because it does not match the existing TerraLens opt-out contact exactly, dropping phone-only `q1_004`, treating LakeHealth Robotics as a new account despite existing CRM account `acct_lakehealth`, and counting duplicate removals as suppressions rather than `no_import`.

Transfer anchors: SP001 through SP004 are anchored by `train_003` and `train_004`. The relevant transferable knowledge is to normalize before matching, dedupe by normalized email before phone-company keys, prefer the most recent source record with source priority as the tie-breaker, preserve contacts with either email or phone, and remove suppressed or opted-out contacts before final import. SP005 and SP006 also benefit from `train_003` because that task establishes the import action counting convention, but they require task-local exploration of q1-specific existing accounts and the new source label. This test keeps the same contact-hygiene operation family while changing the batch, duplicate conflicts, existing-contact overlap, and suppression pattern.
