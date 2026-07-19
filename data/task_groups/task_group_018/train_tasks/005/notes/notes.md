# train_005 Notes

## English Review Notes

This task is part of `SCN_018_court_clerk_disposition_orders_and_financial_entries`, using source examples `E002` and `E003` most directly. It builds the train-set Virginia hybrid operation described in `scratch/task_group_design.md`: two Gloucester County post-disposition financial petitions must be reconciled with case, form, policy, sentencing, probation, and license records. The target records are `VA-CR25-0884-00` / `VA-PET-884A` for Lena Walsh and `VA-CR25-0913-00` / `VA-PET-913A` for Marcus Hill.

Solver-visible materials are `prompt.txt`, `payloads/petition_summaries.json`, `payloads/sentencing_probation_notes.json`, and `payloads/answer_template.json`. The shared environment supplies the authoritative public-data portal through `<TASK_ENV_BASE_URL>`, especially `GET /api/cases`, `GET /api/charges`, `GET /api/payment-policies`, `GET /api/forms`, and `GET /api/financial-petitions`. The local payloads provide realistic counter notes and courtroom/probation notes, including a stale account-fee row and missing identifiers.

The business task is to prepare clerk-ready structured JSON for two first-petition installment agreements, one CC-1375 probation referral status set, two CC-1379 license/payment orders, and placeholder handling. The important constraints are: classify both petitions as initial installments; choose the supportable monthly amounts already consistent with Gloucester's $50-$100 first-petition band; exclude account-management fees because Gloucester policy has a zero account fee; keep Marcus Hill's restitution ahead of fines and costs; calculate monthly schedules through the final partial payment and return-to-court date; and use `TBD from case file` for unknown SSN, driver license number, addresses, phone, probation office, and probation officer fields.

The standard answer uses these determinations. Lena Walsh has total due `$1,435.00`, no restitution, monthly `$85.00`, 17 installments, a `$75.00` final payment on `2026-08-11`, and return date `2026-10-10`. Marcus Hill has restitution `$360.00`, fines/costs `$1,180.00`, total due `$1,540.00`, monthly `$50.00`, 31 installments, a `$40.00` final payment on `2027-10-17`, and return date `2027-12-16`. Lena has a CC-1375 referral for 12 months with report datetime `2025-03-14T08:30:00`; Marcus has no signed CC-1375 referral order. License orders use conviction-date starts: Lena 12 months from `2025-03-11` to `2026-03-11`, Marcus 6 months from `2025-03-17` to `2025-09-17`.

Evaluation has eight whole-point checks and raw weights totaling 18: SP001 petition identity/classification (2), SP002 supportable monthly terms and no down payment (2), SP003 balances plus Marcus restitution priority (3), SP004 Gloucester account-fee exclusion (2), SP005 payment schedule counts/final payments/final dates/return dates (3), SP006 CC-1375 probation status and dates (2), SP007 CC-1379 license dates and durations (2), and SP008 placeholder discipline (2). The checks cover at least four distinct outcomes: petition classification, financial supportability, balance and priority handling, local fee exclusion, schedule computation, probation form status, license order timing, and missing-field handling. Each point is deterministic and earns either its full assigned score or zero.

Transfer value: as a train task, this reinforces the Virginia conventions from `train_003` while adding a second petition and Marcus restitution priority. A solver comparing attempts against the answer can infer that Gloucester first-petition payment orders use an initial installment classification, no down payment, the local monthly band, no account fee, exact monthly schedule math with final partial payment, conviction-date license timing, and strict `TBD from case file` discipline. It also demonstrates that probation referral, license consequence, and payment order fields should remain separate even when they are packaged together.

Likely model pitfalls include copying the stale `$25.00` counter account-fee row, treating Marcus as a subsequent/default petition, applying payments to fines before restitution, inventing driver license or address data, using the charge table's generic DUI duration instead of the packet's 6-month Marcus license entry, omitting the final partial installment, or collapsing Marcus into a probation referral despite the local note saying no CC-1375 order was signed.

Construction record: created by Codex task-builder subagent for `train_005` on 2026-07-18. Files were created only under `task_group/task_group_018/train_tasks/005/`.

## 中文审核说明

本任务属于 `SCN_018_court_clerk_disposition_orders_and_financial_entries`，主要承接来源示例 `E002` 与 `E003`。它实现 `scratch/task_group_design.md` 中的 Virginia 混合型训练任务：书记员需要把 Gloucester County 的两份判后付款申请，与案件、表格、付款政策、量刑、缓刑和驾照暂停记录相互核对。目标记录是 Lena Walsh 的 `VA-CR25-0884-00` / `VA-PET-884A`，以及 Marcus Hill 的 `VA-CR25-0913-00` / `VA-PET-913A`。

求解者可见材料包括 `prompt.txt`、`payloads/petition_summaries.json`、`payloads/sentencing_probation_notes.json` 和 `payloads/answer_template.json`。共享环境通过 `<TASK_ENV_BASE_URL>` 提供法院业务门户，关键端点包括 `GET /api/cases`、`GET /api/charges`、`GET /api/payment-policies`、`GET /api/forms` 和 `GET /api/financial-petitions`。本地 payload 提供柜台摘要与法庭/缓刑备注，其中包含过时的账户管理费行以及若干缺失身份字段。

业务任务是生成书记员可复核的结构化 JSON，覆盖两份首次分期付款申请、一组 CC-1375 缓刑转介状态、两份 CC-1379 驾照/付款命令，以及占位符处理。关键约束包括：两份 petition 都应归类为初始分期；月付款金额应符合 Gloucester 首次申请 `$50-$100` 区间并与财务情况相符；Gloucester 政策下账户管理费为零；Marcus Hill 的 restitution 必须优先于 fines and costs；付款计划必须算到最后一期部分付款和返庭日期；未知 SSN、驾照号、地址、电话、缓刑办公室和缓刑官字段使用 `TBD from case file`。

标准答案的核心结论如下。Lena Walsh 总欠款为 `$1,435.00`，无 restitution，每月 `$85.00`，共 17 期，最后一期 `$75.00`，最后到期日 `2026-08-11`，返庭日 `2026-10-10`。Marcus Hill 有 restitution `$360.00`、fines/costs `$1,180.00`，总欠款 `$1,540.00`，每月 `$50.00`，共 31 期，最后一期 `$40.00`，最后到期日 `2027-10-17`，返庭日 `2027-12-16`。Lena 需要 CC-1375 转介，缓刑 12 个月，报到时间为 `2025-03-14T08:30:00`；Marcus 没有已签署的 CC-1375 转介命令。驾照暂停从定罪日开始：Lena 为 `2025-03-11` 至 `2026-03-11` 的 12 个月，Marcus 为 `2025-03-17` 至 `2025-09-17` 的 6 个月。

评测包含 8 个整点评分项，原始权重合计 18：SP001 petition 身份与分类（2），SP002 可支持月付款和无首付款（2），SP003 欠款金额与 Marcus restitution 优先（3），SP004 Gloucester 账户费排除（2），SP005 付款期数、最后一期、最终日期和返庭日（3），SP006 CC-1375 缓刑状态和日期（2），SP007 CC-1379 驾照暂停日期和期限（2），SP008 缺失字段占位符纪律（2）。这些评分项覆盖 petition 分类、付款能力、金额与优先级、本地费用政策、付款计划计算、缓刑表格状态、驾照命令时间和缺失字段处理等多个不同业务结果；每项均为确定性的全得或零分。

迁移设计方面，本训练任务强化 `train_003` 中的 Virginia 表格和付款习惯，同时加入第二份 petition 与 Marcus 的 restitution 优先级。通过对照标准答案，后续 skill 可以学到 Gloucester 初始分期的分类、无首付款、本地月付款区间、无账户费、按月精确计算最后一期、驾照从定罪日计算，以及未知字段只能使用 `TBD from case file`。它还展示了缓刑转介、驾照后果和付款命令虽然在同一包材料中，但输出结构上应保持分离。

常见错误包括照抄柜台中过时的 `$25.00` 账户费、把 Marcus 当成 subsequent/default petition、先冲抵 fines 而非 restitution、编造驾照号或地址、忽略 Marcus packet 中的 6 个月驾照暂停、漏算最后一期部分付款，或者在本地备注说明没有 CC-1375 命令的情况下仍为 Marcus 建立缓刑转介。

构造记录：由 Codex task-builder subagent 于 2026-07-18 为 `train_005` 创建。所有文件仅写入 `task_group/task_group_018/train_tasks/005/`。
