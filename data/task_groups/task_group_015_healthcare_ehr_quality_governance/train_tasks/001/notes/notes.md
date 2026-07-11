# train_001 Hidden Construction Notes

## English

Data/source lineage: This task is derived from scenario `SCN_015_healthcare_ehr_quality_governance` and source examples E001. It uses the shared EHR quality API generated under `env/` plus task-local payloads in `input/payloads/`.

Task definition: The solver audits a duplicate candidate for the same respiratory patient and decides whether the records are merge-ready while preserving active chart facts.

Scenario fit: The task belongs to healthcare EHR data governance because it requires record-state reasoning, quality-control decisions, source reconciliation, and auditable structured output rather than casual text generation.

Material map: The duplicate candidate endpoint gives the candidate ID and patient IDs; patient endpoints provide demographics and active/inactive clinical lists; audit-log endpoint provides merge-review evidence.

Solution and evaluation basis: The answer is built from matching demographics, lower stable enterprise MRN, active problem/medication/allergy union, and the ready-for-merge audit event.

Scoring goals:
- SP001 (3): Correct merge disposition, canonical target, and source patient.
- SP002 (2): Correct active problem code set preserved after merge.
- SP003 (2): Correct active medication ID set preserved after merge.
- SP004 (2): Correct active allergy label set preserved after merge.
- SP005 (1): Correctly avoid excluding any true duplicate patient record.
- SP006 (2): Correct audit event and merge audit status.
- SP007 (1): Correctly determine no provider contact action is required.
- SP008 (2): Correct stable-MRN merge reason code.

Transfer design: As a train task, it exposes merge direction, active-list preservation, semantic deduplication, and audit evidence conventions through a real reconciliation task.

Construction record: Author Codex; created 2026-07-07; updated 2026-07-07. Major changes: initial task construction with shared generated environment and exact-match evaluator.

## Chinese

数据来源：本任务来自场景 `SCN_015_healthcare_ehr_quality_governance` 和示例 E001。任务使用 `env/` 中生成的共享 EHR 质量管理 API，以及 `input/payloads/` 中的本任务可见材料。

任务定义：The solver audits a duplicate candidate for the same respiratory patient and decides whether the records are merge-ready while preserving active chart facts.

场景适配：本任务属于医疗 EHR 数据治理，因为它要求判断病历状态、核对质量问题、协调多个来源，并输出可审计的结构化结果，而不是生成自由文本。

材料地图：The duplicate candidate endpoint gives the candidate ID and patient IDs; patient endpoints provide demographics and active/inactive clinical lists; audit-log endpoint provides merge-review evidence.

解法与评估依据：The answer is built from matching demographics, lower stable enterprise MRN, active problem/medication/allergy union, and the ready-for-merge audit event.

评分点：
- SP001 (3): Correct merge disposition, canonical target, and source patient.
- SP002 (2): Correct active problem code set preserved after merge.
- SP003 (2): Correct active medication ID set preserved after merge.
- SP004 (2): Correct active allergy label set preserved after merge.
- SP005 (1): Correctly avoid excluding any true duplicate patient record.
- SP006 (2): Correct audit event and merge audit status.
- SP007 (1): Correctly determine no provider contact action is required.
- SP008 (2): Correct stable-MRN merge reason code.

迁移设计：As a train task, it exposes merge direction, active-list preservation, semantic deduplication, and audit evidence conventions through a real reconciliation task.

构造记录：作者 Codex；创建日期 2026-07-07；更新日期 2026-07-07。主要变更：基于共享生成环境和精确匹配评估器完成初版任务构造。
