# Train 001 Notes - M-CRN-041 First Rolling Production Gap Review

## English Audit Notes

Lineage:
- Scenario source: `SCN_017_white_collar_investigation_production_review`.
- Task group: `task_group_017`, operation family "Production/category gap review".
- Matter fixture: `M-CRN-041`, Crownpoint Neurodevices Market Integrity Inquiry.

Task definition:
- The solver acts for the production team before an SEC status call.
- The solver must inspect shared API records and a small partner request payload, then return only structured JSON.
- The task asks for materially deficient first rolling production categories, priority issues, disclosure need, and remediation actions.
- Solver-visible prompt and payload files are English-only and avoid SOP checklists, answers, and scoring weights.

Material map:
- `matters`: `M-CRN-041` identifies SEC Enforcement, subpoena date `2024-03-14`, hold date `2024-03-15`, deadline `2024-08-30`, and regulator notice flag true.
- `subpoena_categories`: relevant scored categories are `CRN-03`, `CRN-04`, `CRN-05`, and `CRN-06`; noisy comparator categories `CR-N001` onward are not part of the standard answer.
- `collection_events`: `CE-0001` records the unavailable G. Weller iPhone, factory reset six days after subpoena, with Signal and WhatsApp unavailable; `CE-0002` records collection of the former QA director mailbox but notes the miscoding.
- `production_logs`: `PL-0001` records the miscoded testing-accuracy email for `CRN-03`; `PL-0002` records 4,232 privileged-coded records, 1,847 logged, and 2,385 unlogged for `CRN-04`; `PL-0003` records 1,247 withheld and zero produced for `CRN-06`.
- `privilege_logs`: `PV-0001` supports the `CRN-04` privilege-log gap; `PV-0002` flags over-designation risk for the counsel communications category.
- `qc_events`: `QC-0001` identifies one miscoded complaint/testing-accuracy item and points to broader complaints category treatment.
- `custodians`: `C-GW-014` is G. Weller with the personal phone/Signal/WhatsApp gap; `C-QA-027` is R. Sen, former QA director, with the testing-accuracy email miscoding.
- `documents`: `DOC-CRN-TEST-ACC-001` is the former QA director email about testing-accuracy concerns, coded non-responsive and not produced.
- `input/payloads/partner_request.json`: gives only the realistic assignment context and output expectations, not answer facts.

Solution and evaluation basis:
- `PI-CRN-PERSONAL-DEVICE`: `CRN-05` is blocked because the personal phone was factory reset after subpoena/hold and Signal/WhatsApp are unavailable. The answer marks this critical, post-hold, notice-required, with regulator notice plus supplemental collection, forensic follow-up, hold refresh, and custodian declaration.
- `PI-CRN-QA-MISCODE`: `CRN-03` needs supplemental production because the testing-accuracy concern email was collected but miscoded non-responsive under a narrow complaints label. The answer ties `CE-0002`, `PL-0001`, `QC-0001`, and `DOC-CRN-TEST-ACC-001`.
- `PI-CRN-PRIV-UNLOGGED`: `CRN-04` has a privilege protocol defect. The controlling counts are withheld/privileged-coded `4232`, logged `1847`, and unlogged `2385`.
- `PI-CRN-COUNSEL-OVERBROAD`: `CRN-06` has an overbroad counsel-communications withholding issue because 1,247 records are withheld and zero are produced.
- The affected category set is exactly `CRN-03`, `CRN-04`, `CRN-05`, and `CRN-06`.
- Disclosure is required because of the post-hold personal-channel loss and the privilege-log production defect. The next-action ranking puts regulator notice first, then source remediation, QC reprocessing, privilege-log supplement, and over-designation review.
- The evaluator uses 8 exact-match scoring points, raw weights in `{1,2,3}`, and emits `score` plus `points`. Self-check against `output/answer.json` returns `score: 1.0`.

Transfer design:
- This train task teaches that subpoena category scope controls over narrower review-guide labels.
- It teaches that missing personal devices and encrypted chat channels are category-impact issues and may require disclosure.
- It teaches privilege-log gap calculation by comparing privileged/withheld totals to logged totals.
- It teaches that a category with all records withheld and none produced can be an over-designation risk even when labeled counsel communications.
- It transfers to later test tasks by preserving the same issue taxonomy, category mapping, controlled actions, and exact count discipline while changing matter IDs and facts.

Construction record:
- Files created only under `task_group/task_group_017/train_tasks/001/`.
- No shared environment files, seed scenario files, other tasks, scratch files, or group metadata were modified.
- The answer schema, expected answer, and evaluator were built from generated API records and the group design brief.
- The evaluator accepts a prediction path as the first argument or through `PREDICTION`, defaults to the task answer, and normalizes list ordering while requiring exact scalar values.

## 中文审计说明

血缘来源：
- 场景来源：`SCN_017_white_collar_investigation_production_review`。
- 任务组：`task_group_017`，操作族为“生产/类别缺口审查”。
- 事项夹具：`M-CRN-041`，Crownpoint Neurodevices Market Integrity Inquiry。

任务定义：
- 解题方扮演 SEC 状态会前的生产审查团队成员。
- 解题方需要查看共享 API 记录和一个小型合伙人请求负载，并且只返回结构化 JSON。
- 任务要求识别第一轮生产中存在实质缺陷的传票类别、优先问题、是否需要披露以及补救动作。
- 面向解题方的 prompt 和 payload 仅使用英文，不包含 SOP 清单、答案或评分权重。

材料映射：
- `matters`：`M-CRN-041` 显示 SEC Enforcement，传票日期 `2024-03-14`，保全日期 `2024-03-15`，截止日期 `2024-08-30`，并有监管通知标记。
- `subpoena_categories`：评分相关类别是 `CRN-03`、`CRN-04`、`CRN-05`、`CRN-06`；`CR-N001` 之后的噪声类别不属于标准答案。
- `collection_events`：`CE-0001` 记录 G. Weller iPhone 不可用，传票后六天恢复出厂设置，Signal 和 WhatsApp 不可用；`CE-0002` 记录前 QA 主管邮箱已收集但存在编码错误。
- `production_logs`：`PL-0001` 记录 `CRN-03` 测试准确性邮件被误编码；`PL-0002` 记录 `CRN-04` 有 4,232 条特权编码记录、1,847 条已登录、2,385 条未登录；`PL-0003` 记录 `CRN-06` 有 1,247 条扣留且零生产。
- `privilege_logs`：`PV-0001` 支撑 `CRN-04` 特权日志缺口；`PV-0002` 标记律师通信类别存在过度指定风险。
- `qc_events`：`QC-0001` 指出一条投诉/测试准确性项目被误编码，并提示投诉类别应按更宽范围处理。
- `custodians`：`C-GW-014` 是 G. Weller，涉及个人手机、Signal、WhatsApp 缺口；`C-QA-027` 是前 QA 主管 R. Sen，涉及测试准确性邮件误编码。
- `documents`：`DOC-CRN-TEST-ACC-001` 是前 QA 主管关于测试准确性问题的邮件，被编码为 non-responsive 且未生产。
- `input/payloads/partner_request.json`：只提供真实工作场景和输出要求，不提供答案事实。

解答与评估依据：
- `PI-CRN-PERSONAL-DEVICE`：`CRN-05` 被阻塞，因为个人手机在传票/保全后被恢复出厂设置，Signal 和 WhatsApp 不可用。标准答案将其列为 critical、post-hold、需要通知，并要求监管通知、补充收集、取证跟进、保全刷新和保管人声明。
- `PI-CRN-QA-MISCODE`：`CRN-03` 需要补充生产，因为测试准确性关注邮件已经收集，但被过窄投诉标签误编码为非响应。标准答案关联 `CE-0002`、`PL-0001`、`QC-0001` 和 `DOC-CRN-TEST-ACC-001`。
- `PI-CRN-PRIV-UNLOGGED`：`CRN-04` 是特权协议缺陷。控制性计数为扣留/特权编码 `4232`、已登录 `1847`、未登录 `2385`。
- `PI-CRN-COUNSEL-OVERBROAD`：`CRN-06` 是律师通信过度扣留问题，因为 1,247 条记录全部扣留且零生产。
- 受影响类别集合精确为 `CRN-03`、`CRN-04`、`CRN-05`、`CRN-06`。
- 由于保全后的个人通信来源损失以及特权日志生产缺陷，需要披露。下一步动作排序为监管通知、来源补救、QC 重处理、特权日志补充、过度指定审查。
- 评估器有 8 个精确匹配评分点，原始权重均在 `{1,2,3}` 中，并输出 `score` 和 `points`。对 `output/answer.json` 自检返回 `score: 1.0`。

迁移设计：
- 本训练任务教会解题方：传票类别范围优先于较窄的内部审查指南标签。
- 本任务教会：缺失个人设备和加密聊天渠道会影响类别完整性，并可能需要披露。
- 本任务教会：特权日志缺口应通过比较特权/扣留总数与已登录总数计算。
- 本任务教会：即便类别名是律师通信，如果所有记录扣留且没有任何生产，也可能存在过度指定风险。
- 这些规则会迁移到后续测试任务，但测试会更换事项 ID、类别名称和具体事实。

构建记录：
- 文件只创建在 `task_group/task_group_017/train_tasks/001/` 下。
- 未修改共享环境、种子场景、其他任务、scratch 文件或任务组元数据。
- 答案 schema、标准答案和评估器均来自生成的 API 记录和任务组设计说明。
- 评估器接受第一个命令行参数或 `PREDICTION` 环境变量作为预测路径，默认使用本任务答案；它会归一化列表顺序，但标量值必须精确匹配。
