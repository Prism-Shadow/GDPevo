# test_005 Notes / 测试 005 说明

## English

Data/source lineage: This task belongs to scenario `SCN_015_healthcare_ehr_quality_governance`, source examples `E001` through `E005`, with the strongest lineage from `E005` referral data-quality audit. The formal brief is the April orthopedic referral audit batch `APR26-ORTHO-B`. The solution is derived from the shared read-only environment data in `task_group/task_group_015/env/data/records.json`, reached by solvers only through the referral, ICD-10, patient search/detail, duplicate candidate, and provider APIs. No task-local payload beyond `answer_template.json` is needed.

Task definition: The solver must audit all rows returned for `APR26-ORTHO-B` and produce normalized JSON. The expected work includes identifying out-of-range ICD-10 chapters for an orthopedic batch, narrative and laterality mismatches, true duplicate referral resubmissions, insurance/patient anomalies that should not be treated as duplicate referrals, authorization and documentation queues, Tier 1/2/3 action assignments, and summary counts. The solver-visible prompt intentionally does not provide a procedural checklist or answer-like hints.

Material map: `GET /api/referrals?batch=APR26-ORTHO-B` supplies the 23 referral rows, their urgency, authorization state, documents received, receiving provider, and coordination notes. `GET /api/icd10/{code}` supplies chapter, laterality requirement, and expected terms. Patient search/detail is needed to separate same-patient duplicates from shared-insurance anomalies. Duplicate-candidate endpoints are useful context for the recurring identity-governance convention, but the referral duplicate group here is a same-patient referral resubmission, not a chart merge candidate. Provider endpoints supply owner provider ids.

Solution basis: The batch has 23 rows and 20 unique patients. Codes outside the Musculoskeletal chapter are `C34.91`, `I25.10`, `S83.241A`, and `S83.242A`, producing invalid/out-of-range referrals `REF-APR-001`, `REF-APR-008`, `REF-APR-012`, `REF-APR-013`, `REF-APR-015`, `REF-APR-018`, and `REF-APR-021`. The mismatch set contains 21 referrals: all except exact matches `REF-APR-019` and `REF-APR-023-DUP`. The true duplicate referral group is `REF-APR-005` and `REF-APR-023-DUP` for patient `P-73008`; both rows are immediate duplicate-blocker action items for consolidation, while `REF-APR-016` is the same patient but a separate urgent clinical referral and is not in that duplicate group. Insurance anomaly `INS-663020` links different patients `P-40720` and `P-73008`, and `P-50831` has two separate clinical referrals (`REF-APR-001`, `REF-APR-011`) that should not be collapsed as duplicates.

Queue basis: `authorization_missing` is the set with authorization status `missing`; `authorization_pending` is reported separately. `records_request` is missing `office_note`. `imaging_follow_up` applies the March audit convention: routine orthopedic musculoskeletal referrals require an x-ray; injury/meniscus codes require both x-ray and MRI; out-of-range orthopedic-batch rows still require appropriate imaging follow-up when the referral packet lacks the baseline orthopedic imaging used for triage.

Tier basis: Tier 1 contains urgent rows with unresolved clinical/action blockers plus the duplicate resubmission that should be immediately consolidated: `REF-APR-007`, `REF-APR-011`, `REF-APR-016`, and `REF-APR-023-DUP`. Tier 3 is reserved for administrative document completion without coding/narrative/auth/duplicate blockers, here only `REF-APR-019`. Remaining blocked rows are Tier 2. There are no validated ready rows with no follow-up.

Evaluation basis: The evaluator has 9 deterministic whole-point checks with raw weights totaling 21: batch identity/counts (3), invalid chapter/code set (3), laterality/narrative mismatch set (2), duplicate group (2), authorization/document queues (2), insurance/patient anomalies (2), Tier 1 action assignments including owner providers (3), Tier 2/Tier 3 split (2), and summary counts (2). Each point is pass/fail with no partial credit. The evaluator checks normalized ids, sets, mappings, and integer counts rather than free-form explanation.

Transfer design: This test is anchored mainly by `train_005` (`MAR26-ORTHO-A`), which teaches through example that orthopedic batch audits require ICD chapter validation, code/narrative/laterality reconciliation, duplicate-vs-insurance distinction, documentation queues, and tier routing. `train_001` and `train_004` reinforce identity and duplicate handling; `train_002` reinforces referral-code reconciliation and provider routing. The test changes the batch, row count, code mix, insurance anomaly, and duplicate shape so solvers still need fresh API exploration.

Likely model pitfalls: Models may trust the task brief's approximate batch size rather than the API's 23 rows; treat Injury S-codes as orthopedic instead of out-of-range chapter rows; merge all `P-73008` referrals instead of only `REF-APR-005`/`REF-APR-023-DUP`; omit one side of the duplicate-group action from Tier 1; confuse shared insurance `INS-663020` with a duplicate patient; omit pending authorizations; or classify all patient-requested-delay notes as Tier 3 despite clinical coding blockers.

Construction record: Created by the task-builder subagent on 2026-07-17. The task folder is `task_group/task_group_015/test_tasks/005/`. The standard answer and evaluator were derived from the shared generated environment records, with the canonical batch count set to the actual API-visible 23 referral rows.

## 中文

数据和来源：本任务属于场景 `SCN_015_healthcare_ehr_quality_governance`，来源示例为 `E001` 到 `E005`，最直接对应 `E005` 的转诊数据质量审计。正式任务是 April 骨科转诊批次 `APR26-ORTHO-B`。标准答案来自共享只读环境数据 `task_group/task_group_015/env/data/records.json`，求解者只能通过转诊、ICD-10、患者搜索/详情、重复候选和服务提供者 API 访问这些信息。除 `answer_template.json` 外没有额外任务本地材料。

任务定义：求解者需要审计 `APR26-ORTHO-B` 返回的全部记录，并输出规范化 JSON。关键结果包括骨科批次中的越界 ICD-10 章节、叙述和左右侧不匹配、真实重复转诊、不能误判为重复的保险/患者异常、授权和文档队列、Tier 1/2/3 行动分配，以及汇总计数。可见提示刻意避免提供步骤清单或答案线索。

材料映射：`GET /api/referrals?batch=APR26-ORTHO-B` 提供 23 条转诊记录，包括紧急程度、授权状态、已收到文档、接收医生和协调备注。`GET /api/icd10/{code}` 提供章节、左右侧要求和预期术语。患者搜索/详情用于区分同一患者重复转诊和共享保险异常。重复候选端点提供身份治理背景，但本任务的重复组是同一患者的转诊重复提交，不是病历合并候选。服务提供者端点用于确认负责人 provider id。

答案依据：该批次有 23 行、20 名唯一患者。骨科批次中非 Musculoskeletal 章节的代码包括 `C34.91`、`I25.10`、`S83.241A`、`S83.242A`，对应 `REF-APR-001`、`REF-APR-008`、`REF-APR-012`、`REF-APR-013`、`REF-APR-015`、`REF-APR-018`、`REF-APR-021`。不匹配集合有 21 条，除完全匹配的 `REF-APR-019` 和 `REF-APR-023-DUP` 外均包含在内。真实重复转诊组是患者 `P-73008` 的 `REF-APR-005` 和 `REF-APR-023-DUP`；这两行都作为需要立即合并处理的 duplicate-blocker 行动项，`REF-APR-016` 则是同一患者的另一条紧急临床转诊，不属于该重复组。保险异常 `INS-663020` 连接不同患者 `P-40720` 和 `P-73008`，`P-50831` 的两条转诊也应作为不同临床审查处理而不是合并。

队列依据：`authorization_missing` 对应授权状态为 `missing` 的记录；`authorization_pending` 单独报告。`records_request` 对应缺少 `office_note`。`imaging_follow_up` 继承 March 审计规则：常规骨科肌骨转诊需要 x-ray；损伤/半月板代码需要 x-ray 和 MRI；越界代码如果仍在骨科批次中，也要在缺少基础骨科分诊影像时进入影像跟进队列。

分层依据：Tier 1 包括有未解决临床/行动阻断的紧急记录，以及需要立即合并处理的重复提交：`REF-APR-007`、`REF-APR-011`、`REF-APR-016`、`REF-APR-023-DUP`。Tier 3 只用于没有编码、叙述、授权或重复阻断的行政文档补全，本任务只有 `REF-APR-019`。其余有阻断的问题记录为 Tier 2。没有完全就绪且无需跟进的记录。

评估依据：评估器包含 9 个确定性整点评分项，原始权重总计 21：批次身份和计数 (3)、无效章节/代码集合 (3)、左右侧/叙述不匹配集合 (2)、重复组 (2)、授权/文档队列 (2)、保险/患者异常 (2)、含负责人分配的 Tier 1 行动项 (3)、Tier 2/Tier 3 拆分 (2)、汇总计数 (2)。每项只有通过或不通过，不给项内部分分。评估器检查规范化 id、集合、映射和整数计数，不评价自由文本。

迁移设计：本测试主要由 `train_005`（`MAR26-ORTHO-A`）锚定，训练样例通过正式答案体现骨科批次审计需要 ICD 章节验证、代码/叙述/左右侧核对、重复和保险异常区分、文档队列及分层路由。`train_001` 和 `train_004` 强化身份与重复处理，`train_002` 强化转诊代码核对和 provider 路由。测试更换了批次、记录数、代码组合、保险异常和重复形态，因此仍需要重新探索 API。

常见陷阱：模型可能相信任务简介中的近似批次数而不是 API 中实际的 23 行；把 Injury 章节 S-code 当作骨科有效代码；把 `P-73008` 的所有转诊都合并，而不是只合并 `REF-APR-005`/`REF-APR-023-DUP`；在 Tier 1 中漏掉重复组的一侧；把共享保险 `INS-663020` 误判为重复患者；遗漏 pending 授权；或者将所有患者要求延迟的备注都归为 Tier 3，即使存在临床编码阻断。

构建记录：由 task-builder subagent 于 2026-07-17 创建。任务目录为 `task_group/task_group_015/test_tasks/005/`。标准答案和评估器依据共享生成环境记录构建，标准批次数采用 API 实际可见的 23 条转诊记录。
