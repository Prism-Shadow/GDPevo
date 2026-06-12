# train_003 Notes
## English

This task belongs to source scenario `SCN_001_crm_marketing_lead_capture`, using source examples `E001`, `E002`, and especially `E003` for contact-data hygiene. It implements the task-group design brief for `train_003`: clean and summarize the HarborCRM raw campaign batch `fall_webinar_import` for CRM import. The shared environment data is in `task_group/task_group_001/env/data/harborcrm_data.json`; public solver access is through the HarborCRM API endpoints for import batches, raw contacts, suppression, CRM accounts, CRM contacts, and policies. The only task-local solver payload is `input/payloads/answer_template.json`.

The solver-visible task asks for a CRM-ready JSON summary, not a mutation of the CRM. The expected output includes batch metadata, surviving cleaned contacts, duplicate metadata, removal metadata, action totals, and the campaign member count. The visible prompt deliberately avoids a procedural SOP list; solvers must inspect the public policy endpoint and reconcile the raw batch with CRM and suppression data.

The important source records are raw rows `fw_001` through `fw_008`. `fw_002` wins over `fw_001` for Dana Ruiz because the normalized email matches and `fw_002` is more recent. `fw_008` wins over `fw_003` for Evan Blake because the normalized email and timestamp match, and `partner_upload` outranks `webinar_form` in source priority. `fw_005` survives as an email-only contact. `fw_006` is unusable because it lacks both normalized email and normalized phone. `fw_004` and `fw_007` are suppressed: `fw_004` also matches an opted-out existing CRM contact, and `fw_007` appears in the suppression list. HelioWare already exists as CRM account `acct_helio_ware`, so Dana Ruiz is an `update_existing` import action with no existing contact id. Monarch Foods and Quartz Foods have no matching CRM account and use `create_account`.

The material map is:

- `GET /api/import_batches` identifies campaign code `WEB-FALL-2026` for `fall_webinar_import`.
- `GET /api/import_batches/fall_webinar_import/raw_contacts` provides the raw rows to normalize, suppress, dedupe, and import.
- `GET /api/import_batches/fall_webinar_import/suppression` provides suppression matches by normalized email or phone.
- `GET /api/crm/accounts` determines whether a surviving contact maps to an existing account.
- `GET /api/crm/contacts` identifies opted-out existing contacts and possible existing contact matches.
- `GET /api/policies` exposes the general normalization, dedupe, and source-priority conventions.

The standard answer in `output/answer.json` has three clean contacts sorted by row id: `fw_002`, `fw_005`, and `fw_008`. Email values are lowercase and trimmed. Phone values are digits-only, preserving a leading country digit when present in the winning row. Duplicate removal count is `2`, with duplicate keys `email:dana.ruiz@helioware.example` and `email:evan.blake@quartzfoods.example`. Removal counts are one unusable row and two suppressed rows. Import action totals are `create_account: 2`, `update_existing: 1`, `no_import: 3`, and `suppress: 2`. Campaign member import count is `3`.

The evaluator has seven scoring points, matching the design:

- SP001, weight 3: exact ordered surviving cleaned contact IDs.
- SP002, weight 2: normalized email values by survivor id.
- SP003, weight 2: normalized phone values by survivor id.
- SP004, weight 2: duplicate removal count and duplicate keys with winner and removed row ids.
- SP005, weight 2: unusable and suppressed removal counts with the relevant removed rows.
- SP006, weight 2: import action totals.
- SP007, weight 1: campaign member import count.

Likely pitfalls include keeping both duplicate rows, picking the webinar form over the partner upload on equal timestamp, dropping Kenji Sato because the phone is blank, treating suppressed rows as ordinary `no_import` rather than `suppress`, normalizing Evan Blake from the losing row instead of the winning row, and assuming HelioWare requires account creation even though it exists in CRM.

As a train task, this should teach transfer habits for `test_003`: read public policies, normalize before matching, suppress before final import, handle existing opted-out contacts, dedupe by normalized email before phone-company keys, and prefer the most recent/highest-priority source record. The train-derived skill should capture the shape of the hygiene workflow without memorizing these row ids.
