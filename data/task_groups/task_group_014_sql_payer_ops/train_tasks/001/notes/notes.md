# train_001 Notes: Intake and triage exception batch

## English

Task purpose: this train task teaches solvers to query the shared SQLite payer operations service, locate the `train_intake_batch` authorization rows, join the operational reference tables, and apply intake checks in first-failure order.

Data lineage: target case IDs come from `data_manifest.json` and `authorization_requests.target_bucket = 'train_intake_batch'`: `AUTH00001` through `AUTH00006`. The answer was derived from `authorization_requests`, `auth_lines`, `service_codes`, `members`, `plans`, `providers`, `facilities`, `existing_authorizations`, and `state_sla_rules`.

Solution basis: `AUTH00001`, `AUTH00002`, and `AUTH00006` halt for duplicate authorization matches. `AUTH00003` halts for unprocessed COB. `AUTH00004` halts because the service was rendered before submission and also has a requesting-provider sanction item. `AUTH00005` halts because `S9999` is not a covered service. All target cases are routine, with SLA due values calculated from the most restrictive applicable state rule or plan rule. Notice count excludes the COB hold.

Evaluation design: the evaluator awards exact-match business-result points only. It checks case dispositions, gold-card/review decisions, SLA results, duplicate handling, provider item identification, and summary counts. It does not score prose.

Construction record: solver-visible files disclose only the fixed synthetic Basic Auth credentials needed for `<TASK_ENV_BASE_URL>/query`; they do not include localhost, database paths, raw answers, or hidden APIs.

## 中文

任务目的：这个训练任务让解题者通过共享的 SQLite 付款方运营查询服务，找到 `train_intake_batch` 授权记录，连接运营参考表，并按“第一个失败项”顺序执行受理检查。

数据来源：目标病例 ID 来自 `data_manifest.json` 以及 `authorization_requests.target_bucket = 'train_intake_batch'`，即 `AUTH00001` 到 `AUTH00006`。标准答案由 `authorization_requests`、`auth_lines`、`service_codes`、`members`、`plans`、`providers`、`facilities`、`existing_authorizations` 和 `state_sla_rules` 推导得到。

解题依据：`AUTH00001`、`AUTH00002` 和 `AUTH00006` 因重复授权匹配而停止受理；`AUTH00003` 因 COB 未处理而暂停；`AUTH00004` 因服务已在提交前完成而暂停，同时存在请求医生制裁状态；`AUTH00005` 因 `S9999` 为非覆盖服务而拒绝。所有目标病例均为 routine，SLA 到期时间根据最严格的适用州规则或计划规则计算。通知数量不包括 COB 暂停。

评估设计：评估器只按精确匹配的业务结果给分，检查病例处置、gold-card/审核决策、SLA 结果、重复授权处理、提供者项目识别和汇总计数，不给自由文本打分。

构建记录：解题者可见文件只公开访问 `<TASK_ENV_BASE_URL>/query` 所需的固定合成 Basic Auth 凭据，不包含 localhost、数据库路径、原始答案或隐藏答案 API。
