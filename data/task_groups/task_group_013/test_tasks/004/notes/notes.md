# Chronic Care Enrollment Panel: Renal Diabetes Outreach

## English Notes

This is `test_004` for `task_group_013`, derived from scenario `SCN_013_healthcare_patient_intake_transfer`. It is the chronic-care enrollment test counterpart to `train_004` and uses the same Cedar Ridge Intake Coordination Portal environment. The main source-example lineage is `E004` for chronic-care enrollment and outreach planning, with `E003` providing the chart-readiness convention that an existing patient record is not automatically a ready chart. The solver-visible files are `input/prompt.txt`, `input/payloads/answer_template.json`, and `input/payloads/program_policy.json`; all patient and chart evidence comes from the read-only environment via `/programs/RENAL-DM-2026B/candidates`, `/patients/{patient_id}`, `/chart/{patient_id}`, and optional `/query`.

The task asks for a panel for program `RENAL-DM-2026B` as of `2026-07-15`. The current program candidate endpoint returns ten candidates: seeded renal-diabetes candidates `P033` through `P039`, plus noisy candidates `P047`, `P062`, and `P101`. The standard answer includes all ten rows sorted by `patient_id`. The answer schema intentionally uses controlled reason codes, enum disposition values, normalized renal chart artifact names, and structured monitoring packages to avoid free-form matching.

The construction rule is anchored in `train_004` and made explicit for this renal program in `program_policy.json`: eligibility is separate from final disposition. For this renal-diabetes program, candidates are eligible when they are on the renal-diabetes target condition and have an active diabetes diagnosis in clinical history. The renal program flag is represented by the candidate `target_condition` value `renal_diabetes`; CKD or a literal renal-diabetes diagnosis string is not required. The chart still must be ready enough for enrollment. Patients `P033` through `P039` are eligible. `P047`, `P062`, and `P101` are rejected as wrong-target candidates; `P047` and `P101` also declined consent, and `P101` lacks active renal-diabetes diagnosis evidence.

Enrollment disposition uses consent and chart readiness after eligibility. `P036` and `P039` enroll. `P033` is held because the chart lacks a program-consent artifact even though the candidate row carries signed consent; this tests the chart-artifact convention from `train_004` and `train_005`. `P034` is held because `existing_chart` is false. `P035` is held because the current candidate consent status is missing, despite a historical chart consent artifact. `P037` is held because `existing_chart` is false and demographics are incomplete. `P038` is held because candidate consent is missing and the vitals/labs artifacts are drafts, so they do not count as recent renal chart artifacts.

Follow-up cadence follows the chronic-care pattern from `train_004` with renal-specific package names. Enrolled standard renal-diabetes patients are monthly; high-touch patients are weekly. `P039` is weekly because of recent hospitalization. Held patients are `deferred`; rejected patients are `none`. Outreach channel uses the program candidate's preferred outreach value when there is a usable contact path in the patient profile, resulting in phone for `P033`, `P036`, `P038`, `P039`, `P047`, and `P101`; SMS for `P034`; portal for `P035`; email for `P037` and `P062`; and none for no candidate.

The monitoring package is normalized. `P036` receives `standard_renal_dm` with BP cuff, glucometer, renal lab order for eGFR/UACR/CMP, and a 30-day check-in. `P039` receives `high_touch_renal_dm` with those core components plus medication reconciliation and care-plan setup, with a seven-day check-in. Held patients receive `deferred` packages containing the needed remediation components: `P033` needs the signed consent filed through a chart update request, `P035` needs a consent packet, `P037` needs a chart update request, and `P038` needs a consent packet, renal lab refresh request, and chart update request. Rejected patients receive `not_applicable`.

The evaluator has seven whole scoring points with raw weights `[3, 3, 2, 2, 1, 2, 1]`: candidate coverage and eligibility set, enrollment status plus reason-code sets, follow-up cadence, renal-specific missing chart artifacts, outreach channel, monitoring package, and cohort summary counts. These points cover at least four distinct business outcomes: eligibility/disposition, chart readiness, outreach operations, monitoring setup, and aggregation. Each point is all-or-nothing and normalizes set-like arrays before comparison. The provided `output/answer.json` self-scores to `1.0`.

Transfer anchors: `train_004` anchors chronic-care enrollment conventions, including eligibility versus disposition, consent handling, cadence assignment, outreach channel normalization, monitoring package structure, and summary counting. `train_005` reinforces chart activation logic: a patient or referral can exist in the system while still lacking required structured chart artifacts. `train_003` reinforces that draft or incomplete clinical documents do not satisfy readiness checks. The renal test changes the program code, patient cohort, reason-code vocabulary, and program-specific monitoring artifacts while preserving the same inferred operating habits.

Likely model pitfalls include treating the candidate list as already enrolled, omitting noisy wrong-target candidates, accepting draft labs/vitals for `P038`, ignoring `existing_chart` false for `P034` and `P037`, using free-text reason summaries instead of enum codes, or computing summary counts from only enrolled patients rather than all ten candidates.

Construction record: created by Codex task-builder for `test_004` on 2026-07-17. The task files are confined to `task_group/task_group_013/test_tasks/004/`.

## 中文说明

这是 `task_group_013` 的 `test_004`，来源于 `SCN_013_healthcare_patient_intake_transfer`。它是慢病项目纳入工作流的测试任务，对应训练任务 `train_004`，并使用同一个 Cedar Ridge Intake Coordination Portal 只读环境。主要来源示例是 `E004` 的慢病纳入和外联规划，另由 `E003` 支持病历就绪规则：患者记录存在并不等于病历材料已经满足纳入要求。求解者可见文件包括 `input/prompt.txt`、`input/payloads/answer_template.json` 和 `input/payloads/program_policy.json`；证据来自 `/programs/RENAL-DM-2026B/candidates`、`/patients/{patient_id}`、`/chart/{patient_id}` 以及可选的 `/query`。

本任务要求在 `2026-07-15` 为项目 `RENAL-DM-2026B` 生成面板。候选人端点返回十名候选人：种子肾病糖尿病候选人 `P033` 到 `P039`，以及噪声候选人 `P047`、`P062`、`P101`。标准答案按 `patient_id` 排序并包括全部十人。答案结构使用受控原因码、枚举状态、标准化肾病相关缺失病历材料和结构化监测包，避免依赖自由文本评分。

构造规则由 `train_004` 锚定，并在 `program_policy.json` 中对本肾病项目作显式说明：项目资格和最终处置是两个不同判断。本肾病糖尿病项目中，候选人的 `target_condition` 必须是 `renal_diabetes`，并且临床史中要有活动糖尿病诊断；肾病项目标志由候选记录的目标字段表示，不要求 CKD 或临床史中出现字面量 renal_diabetes 诊断。`P033` 到 `P039` 符合项目资格。`P047`、`P062`、`P101` 因目标项目不符而拒绝；其中 `P047` 和 `P101` 还拒绝同意，`P101` 还缺少活动肾病糖尿病诊断证据。

资格确认之后，再用同意状态和病历就绪情况决定 `enroll`、`hold` 或 `reject`。`P036` 和 `P039` 可以纳入。`P033` 因病历中缺少项目同意材料而暂缓；这用于测试从 `train_004` 和 `train_005` 迁移来的结构化病历材料要求。`P034` 因没有活动病历而暂缓。`P035` 因候选记录中的当前同意状态缺失而暂缓，即使历史病历中有同意材料。`P037` 因没有活动病历且人口统计信息不完整而暂缓。`P038` 因当前同意缺失且生命体征、化验为 draft 状态而暂缓。

随访频率沿用 `train_004` 的慢病逻辑，并换成肾病项目语义。标准肾病糖尿病纳入患者为 monthly，高接触患者为 weekly。`P039` 因近期住院为 weekly。暂缓患者为 deferred，拒绝患者为 none。外联渠道优先使用候选记录中的可用偏好，结果是 `P033`、`P036`、`P038`、`P039`、`P047`、`P101` 为 phone，`P034` 为 sms，`P035` 为 portal，`P037` 和 `P062` 为 email。

监测包使用结构化枚举。`P036` 的 `standard_renal_dm` 包含血压计、血糖仪、eGFR/UACR/CMP 肾病化验单和 30 天首次检查。`P039` 的 `high_touch_renal_dm` 在核心组件上增加用药核对和护理计划建立，7 天首次检查。暂缓患者使用 `deferred` 包：`P033` 需要通过病历更新请求归档已签署同意，`P035` 需要同意书，`P037` 需要病历更新请求，`P038` 需要同意书、肾病化验刷新请求和病历更新请求。拒绝患者为 `not_applicable`。

评估器包含七个整点评分项，原始权重为 `[3, 3, 2, 2, 1, 2, 1]`，分别检查候选人覆盖和资格集合、纳入状态和原因码、随访频率、肾病相关缺失病历材料、外联渠道、监测包和汇总计数。这些评分点覆盖资格和处置、病历就绪、外联操作、监测设置和汇总统计等不同业务结果。每项只给满分或零分，并对集合字段做规范化比较。随附的 `output/answer.json` 自评分为 `1.0`。

迁移锚点：`train_004` 提供慢病项目纳入的核心经验，包括资格与处置分离、同意状态处理、随访频率、外联渠道、监测包结构和汇总计数。`train_005` 强化病历激活逻辑，即系统中存在患者或转诊记录不代表结构化病历材料已经满足要求。`train_003` 强化 draft 或不完整临床文档不能满足就绪检查。测试任务改变了项目代码、患者集合、原因码词汇和肾病项目监测内容，但保留了同一类操作习惯。

常见错误包括把候选列表直接当成已纳入名单、漏掉目标不符的噪声候选人、把 `P038` 的 draft 化验和生命体征当作有效材料、忽略 `P034` 和 `P037` 的非活动病历、用自由文本原因替代枚举原因码，或者只按纳入患者计算汇总而不是按全部十名候选人计算。

构造记录：由 Codex task-builder 于 2026-07-17 创建 `test_004`。文件范围仅限 `task_group/task_group_013/test_tasks/004/`。
