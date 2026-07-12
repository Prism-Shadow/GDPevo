# train_005 Hidden Construction Notes

## English

Data/source lineage: This task is derived from scenario `SCN_015_healthcare_ehr_quality_governance` and source examples E002, E004. It uses the shared EHR quality API generated under `env/` plus task-local payloads in `input/payloads/`.

Task definition: The solver reviews a referral and chart, determines the required allergy and diagnosis updates, and decides whether the referral can be sent.

Scenario fit: The task belongs to healthcare EHR data governance because it requires record-state reasoning, quality-control decisions, source reconciliation, and auditable structured output rather than casual text generation.

Material map: Patient endpoints provide problems and encounters; the referral endpoint supplies the reason and referring context; provider records identify the receiving specialist.

Solution and evaluation basis: The answer is based on the severe contrast allergy requirement, I50.22 diagnosis alignment, recent encounter evidence, and absence of unresolved blockers.

Scoring goals:
- SP001 (3): Correct severe iodinated contrast allergy update.
- SP002 (3): Correct heart-failure diagnosis update.
- SP003 (2): Correct recent encounter evidence set.
- SP004 (1): Correct referral target provider and specialty.
- SP005 (2): Correct unresolved issue set.
- SP006 (2): Correct send-ready status.
- SP007 (1): Correct required letter merge fields.
- SP008 (1): Correct safety flag for contrast allergy.

Transfer design: As a train task, it reinforces allergy completeness, diagnosis-code alignment, recent-evidence selection, and send-readiness conventions.

Construction record: Author Codex; created 2026-07-07; updated 2026-07-07. Major changes: initial task construction with shared generated environment and exact-match evaluator.

## Chinese

数据来源：本任务来自场景 `SCN_015_healthcare_ehr_quality_governance` 和示例 E002, E004。任务使用 `env/` 中生成的共享 EHR 质量管理 API，以及 `input/payloads/` 中的本任务可见材料。

任务定义：The solver reviews a referral and chart, determines the required allergy and diagnosis updates, and decides whether the referral can be sent.

场景适配：本任务属于医疗 EHR 数据治理，因为它要求判断病历状态、核对质量问题、协调多个来源，并输出可审计的结构化结果，而不是生成自由文本。

材料地图：Patient endpoints provide problems and encounters; the referral endpoint supplies the reason and referring context; provider records identify the receiving specialist.

解法与评估依据：The answer is based on the severe contrast allergy requirement, I50.22 diagnosis alignment, recent encounter evidence, and absence of unresolved blockers.

评分点：
- SP001 (3): Correct severe iodinated contrast allergy update.
- SP002 (3): Correct heart-failure diagnosis update.
- SP003 (2): Correct recent encounter evidence set.
- SP004 (1): Correct referral target provider and specialty.
- SP005 (2): Correct unresolved issue set.
- SP006 (2): Correct send-ready status.
- SP007 (1): Correct required letter merge fields.
- SP008 (1): Correct safety flag for contrast allergy.

迁移设计：As a train task, it reinforces allergy completeness, diagnosis-code alignment, recent-evidence selection, and send-readiness conventions.

构造记录：作者 Codex；创建日期 2026-07-07；更新日期 2026-07-07。主要变更：基于共享生成环境和精确匹配评估器完成初版任务构造。
