# train_005 Notes

## English

Data lineage: This task is derived from `SCN_003_crm_service_ticket_resolution`, with the strongest anchor in telecom support example `E002`. The visible worklist names five mobile-data cases; the API provides cases, lines, devices, plans, and bills.

Task definition: The solver must decide the primary and secondary operation for each data-support case, calculate any data-refuel charge, and summarize worklist action families.

Scenario fit: The task captures contact-center data recovery where the correct route depends on distinguishing user phone settings, carrier line settings, usage-limit recovery, and human transfer.

Material map: `/api/cases/<id>` gives case context; `/api/lines/<id>` and `/api/plans/<id>` support refuel and roaming decisions; `/api/devices/<id>` supports data saver, network mode, and mobile-data switch decisions.

Solution and evaluation basis: `CASE-2501` requires 2.0 GB refuel at 2.00 USD/GB; `CASE-2502` requires carrier line roaming enablement; the remaining three are device-setting fixes. There are 8 exact-match scoring points.

Transfer design: As a train task, it reinforces the distinction between phone roaming and carrier line roaming, data-limit recovery with price calculation, and slow-data setting fixes.

Construction record: Created by Codex on 2026-06-01. Major change: initial task construction for `task_group_003`.

