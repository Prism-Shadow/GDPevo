# train_005 Hidden Notes

## English

This task belongs to `task_group_001`, source scenario `SCN_001_crm_marketing_lead_capture`, using source examples `E001`, `E002`, and `E003` as design lineage. The concrete task brief is the train prospecting-plus-CRM-enrichment task: prioritize robotics exhibitors from `AquaFarm Robotics Forum 2026` (`show_id` `aquafarm_robotics_2026`) and identify existing CRM overlaps.

The visible inputs are `input/prompt.txt`, `input/payloads/answer_template.json`, and the shared HarborCRM API under `task_group_001/env/`. The relevant environment data is in `env/data/harborcrm_data.json` and is publicly reachable through `/api/tradeshows/aquafarm_robotics_2026/exhibitors`, `/api/tradeshows/aquafarm_robotics_2026/meeting_interest`, `/api/crm/accounts`, `/api/crm/contacts`, and `/api/policies`. No task-local answer data is exposed to solvers.

The task fits the group because it exercises the same front-of-funnel CRM workflow as the source trade-show prospecting example: turn a noisy exhibitor directory and CRM overlap evidence into an import-ready account plan. It also reinforces the group transfer rules for manufacturer/OEM qualification, distributor/service exclusion, controlled platform labels, existing-account update decisions, and structured CRM action enums.

Material map: `prompt.txt` states the business request, target show ID, API surfaces, ranking rule, and opportunity sizing rule. `answer_template.json` defines the required JSON shape, enum values, ordering rules, and integer USD precision. `output/answer.json` is the standard answer. `eval/eval.sh` delegates to `eval/evaluator.py`, which exact-checks six scoring points and prints a JSON score report.

Solution basis: AquaFarm has five exhibitors. Three qualify because they are manufacturers or OEMs: `ReefWorks Robotics`, `Pelagic Droneworks`, and `ClearPen Optics`. `ReefWorks Robotics` is already present in CRM as `acct_reefworks`, so its action is `update_existing`; the other two qualified exhibitors have no CRM account ID and use `create_account`. Two exhibitors are excluded: `FarmGate Analytics` is a service provider and `SouthPier Robotics Supply` is a distributor. Meeting-interest records rank the qualified leads as ReefWorks first (`requested_demo=true`, score 93), Pelagic second (`requested_demo=true`, score 88), and ClearPen third (`requested_demo=false`, score 64). Priority tiers and opportunity estimates are A/USD 120000, B/USD 90000, and C/USD 50000 respectively, for a total of USD 260000. Platform coverage counts are AUV 1, ROV 1, and Underwater Camera 2.

Evaluation basis: six scoring points are used. SP001 weight 3 checks the ranked qualified robotics lead order. SP002 weight 2 checks per-lead platform coverage and aggregate platform counts. SP003 weight 2 checks CRM action and account ID per ranked lead. SP004 weight 2 checks the excluded non-manufacturer accounts and reasons. SP005 weight 2 checks priority tiers, per-lead opportunity estimates, and total estimated opportunity. SP006 weight 1 checks qualified count, CRM overlap count, and overlap account IDs. All checks are exact after simple structural normalization; there is no free-text scoring.

Transfer design: solving this train task should teach that prospecting qualification depends on relationship type and platform manufacturing authority, not on keyword mentions alone. It should also teach that CRM overlaps should normally become updates rather than account creates, and that near-miss robotics-related companies must still be carried in an explicit exclusion list with controlled reasons. These habits anchor the later test prospecting tasks without exposing their answers.

Construction record: authored by Codex task-builder for `train_005` on 2026-06-01. Created the prompt, answer template, hidden notes, standard answer, evaluator helper, and eval entry point. The environment data itself was not modified.

