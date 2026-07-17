# train_001 Notes

## English

Data/source lineage: This task belongs to `SCN_015_healthcare_ehr_quality_governance`, using the duplicate-patient governance pattern from source example `E001` and the shared generated environment for `task_group_015`. The task-specific visible files are `input/prompt.txt`, `input/payloads/answer_template.json`, and `input/payloads/merge_packet_request.json`. The answer is derived from the public business API data in `env/data/records.json`, especially duplicate candidate `DUP-TR-001`, patients `P-31014` and `P-88420`, clinical lists, documents, audit logs, and the provider directory.

Task definition: The solver must produce a normalized duplicate-chart merge readiness packet. The packet identifies the canonical target and source, merge disposition, active condition/medication/allergy key unions to preserve, demographic and duplicate-candidate match/conflict signals, evidence IDs, and the specialist/provider contact needed for the packet. The visible prompt names the candidate and patient IDs but does not provide the operational sequence.

Scenario fit: The task represents an EHR quality-governance workflow where duplicate shells must be resolved without losing active clinical state or audit provenance. It coordinates identity data, clinical-list endpoints, document provenance, audit events, and provider contact records, matching the healthcare data-operations scenario rather than a simple lookup task.

Material map: `GET /api/duplicates/DUP-TR-001` supplies candidate status, patient pair, match/conflict labels, and merge preview fields. `GET /api/patients/{id}` supplies canonical status, demographics, and primary care provider. The condition, medication, and allergy endpoints supply the authoritative active normalized-key unions. Document endpoints identify `DOC-MERGE-TR-001-A` and `DOC-CARD-TR-001`; audit-log queries identify `AUD-TR-001-A` and `AUD-TR-001-B`. `GET /api/providers/PRV-CARD-020` supplies the Summit Heart Center cardiology contact for the external cardiology continuity document, and `PRV-PCP-001` supplies the primary care contact.

Solution and evaluation basis: The canonical target is `P-31014` and the source is `P-88420`; `P-88420` is already marked as a duplicate with canonical patient `P-31014`, and the duplicate candidate is open with strong match signals. The disposition is `ready_to_merge`, while the explicit merge-decision block uses `merge_ready`, `manual_review_required: false`, and reason codes `active_duplicate_candidate`, `duplicate_record_already_points_to_target`, and `strong_identity_match`. The active condition union is `copd`, `coronary_artery_disease`, `diabetes_type_2`, `hypertension`, and `right_knee_oa`. The active medication union is `aspirin`, `baseline_med`, and `metformin`. The active allergy union is `baseline_allergy`, `iodinated_contrast`, and `penicillin`. The `active_list_reconciliation` field records that patient active-list endpoints are authoritative over an incomplete duplicate preview when endpoint-only active keys exist. The candidate match signals are `name_variant`, `same_dob`, `same_insurance`, `same_phone`, and `shared_external_cardiology_document`; the conflict signal is `address_abbreviation`. The answer also names unrelated distractor evidence that must stay out of the merge packet, and `document_selection_policy` records that packet documents come from identity or external-continuity evidence rather than generic chart summaries.

The evaluator has ten whole-point scoring goals with raw weights totaling 20: source/target/disposition (3), merge decision and packet readiness (2), condition union (2), medication union (2), allergy union (2), match/conflict signals (2), document evidence (2), audit evidence (2), active-list/source-precedence and distractor exclusion (2), and specialist/provider contact (1). Each point is all-or-nothing. Likely model pitfalls include relying only on the duplicate preview instead of verifying active clinical-list endpoints, choosing the duplicate shell as target, omitting source-shell cardiology evidence, including unrelated chart-summary documents as merge evidence, or returning unnormalized prose instead of JSON.

Transfer design: As a train task, this exposes transferable duplicate-governance conventions through the completed answer: choose the durable canonical target rather than the source shell, preserve active clinical state by normalized clinical meaning, separate match and conflict signals, carry explicit merge-readiness fields, exclude distractor rows, and include provenance/contact evidence needed for a merge packet. These conventions anchor later duplicate and handoff tasks without making the prompt a tutorial.

Construction record: Created by Codex task-builder subagent for `train_001` on 2026-07-17. Initial version creates the prompt, request payload, template, gold answer, evaluator, and bilingual notes.

## 中文

数据来源：本任务属于 `SCN_015_healthcare_ehr_quality_governance`，继承来源示例 `E001` 的重复患者治理模式，并使用 `task_group_015` 的共享生成环境。任务可见文件包括 `input/prompt.txt`、`input/payloads/answer_template.json` 和 `input/payloads/merge_packet_request.json`。标准答案来自环境中的业务数据，重点是重复候选 `DUP-TR-001`、患者 `P-31014` 与 `P-88420`、临床清单、文档、审计日志和服务提供者目录。

任务定义：求解者需要输出规范化的重复病历合并准备包。结果要给出规范目标病历和来源病历、合并处置、需要保留的活动问题/用药/过敏规范键并集、人口学与重复候选的匹配和冲突信号、证据 ID，以及合并包需要联系的专科或服务提供者。可见提示只给出候选和患者 ID，不提供操作步骤。

场景适配：该任务模拟 EHR 质量治理中的重复壳记录处理。正确处理必须同时考虑身份数据、活动临床状态、文档来源、审计事件和联系信息，符合医疗数据运营场景，而不是单一字段查询。

材料映射：`GET /api/duplicates/DUP-TR-001` 提供候选状态、患者组合、匹配/冲突标签和合并预览。`GET /api/patients/{id}` 提供规范状态、人口学信息和主诊提供者。问题、用药和过敏端点提供权威的活动规范键并集。文档端点确认 `DOC-MERGE-TR-001-A` 和 `DOC-CARD-TR-001`；审计日志确认 `AUD-TR-001-A` 和 `AUD-TR-001-B`。`GET /api/providers/PRV-CARD-020` 提供 Summit Heart Center 的心内科联系信息，`PRV-PCP-001` 提供初级保健联系信息。

答案与评估依据：规范目标为 `P-31014`，来源为 `P-88420`；`P-88420` 已标记为指向 `P-31014` 的重复记录，且候选具有强匹配信号。处置为 `ready_to_merge`，显式合并决策块使用 `merge_ready`、`manual_review_required: false`，并给出 `active_duplicate_candidate`、`duplicate_record_already_points_to_target` 和 `strong_identity_match` 三个原因代码。活动问题并集为 `copd`、`coronary_artery_disease`、`diabetes_type_2`、`hypertension` 和 `right_knee_oa`。活动用药并集为 `aspirin`、`baseline_med` 和 `metformin`。活动过敏并集为 `baseline_allergy`、`iodinated_contrast` 和 `penicillin`。`active_list_reconciliation` 字段记录：当患者活动列表端点中存在合并预览遗漏的活动键时，以活动列表端点为准。匹配信号为 `name_variant`、`same_dob`、`same_insurance`、`same_phone` 和 `shared_external_cardiology_document`；冲突信号为 `address_abbreviation`。答案还列出不应进入合并包的干扰证据，`document_selection_policy` 说明合并包文档来自身份或外部连续性证据，而不是通用 chart summary。

评估器包含 10 个整点评分项，原始权重合计 20：来源/目标/处置 3 分，合并决策和包就绪性 2 分，问题并集 2 分，用药并集 2 分，过敏并集 2 分，匹配/冲突信号 2 分，文档证据 2 分，审计证据 2 分，活动列表来源优先级和干扰项排除 2 分，专科或服务提供者联系信息 1 分。每项只有通过或不通过。常见错误包括只依赖重复候选预览而不核对活动临床清单、把重复壳记录选为目标、遗漏来源壳中的心内科证据、把无关 chart summary 当作合并证据，或输出非规范 JSON。

迁移设计：作为训练任务，本任务通过标准答案体现可迁移经验：选择持久规范记录作为目标，按规范临床含义保留活动状态，区分匹配和冲突信号，保留显式合并就绪字段，排除干扰记录，并为合并包记录来源证据与联系信息。这些经验可迁移到后续重复治理和交接包任务，但不会在可见提示中写成教程。

构建记录：由 Codex task-builder subagent 于 2026-07-17 为 `train_001` 创建。初版包含提示、请求载荷、答案模板、标准答案、评估器和双语说明。
