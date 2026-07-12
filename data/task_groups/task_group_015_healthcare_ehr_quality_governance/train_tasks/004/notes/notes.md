# train_004 Hidden Construction Notes

## English

Data/source lineage: This task is derived from scenario `SCN_015_healthcare_ehr_quality_governance` and source examples E004. It uses the shared EHR quality API generated under `env/` plus task-local payloads in `input/payloads/`.

Task definition: The solver validates a FHIR-like orthopedic service request draft for structured order fields, SBAR completeness, linked evidence, and signing readiness.

Scenario fit: The task belongs to healthcare EHR data governance because it requires record-state reasoning, quality-control decisions, source reconciliation, and auditable structured output rather than casual text generation.

Material map: The service-request endpoint contains the draft; patient encounters provide chart evidence; the codebook and provider records provide terminology and specialty context.

Solution and evaluation basis: The answer accepts the orthopedic service code and order fields but blocks signing because the Recommendation SBAR section is blank.

Scoring goals:
- SP001 (1): Correct request and patient identifiers.
- SP002 (3): Correct service code, specialty, status, and priority.
- SP003 (3): Correct SBAR section completeness.
- SP004 (2): Correct linked chart evidence encounter.
- SP005 (2): Correct laterality consistency decision.
- SP006 (2): Correct ready-to-sign boolean.
- SP007 (2): Correct blocker code list.

Transfer design: As a train task, it teaches order-field validation, SBAR section interpretation, evidence linking, and ready-to-sign blockers.

Construction record: Author Codex; created 2026-07-07; updated 2026-07-07. Major changes: initial task construction with shared generated environment and exact-match evaluator.

## Chinese

数据来源：本任务来自场景 `SCN_015_healthcare_ehr_quality_governance` 和示例 E004。任务使用 `env/` 中生成的共享 EHR 质量管理 API，以及 `input/payloads/` 中的本任务可见材料。

任务定义：The solver validates a FHIR-like orthopedic service request draft for structured order fields, SBAR completeness, linked evidence, and signing readiness.

场景适配：本任务属于医疗 EHR 数据治理，因为它要求判断病历状态、核对质量问题、协调多个来源，并输出可审计的结构化结果，而不是生成自由文本。

材料地图：The service-request endpoint contains the draft; patient encounters provide chart evidence; the codebook and provider records provide terminology and specialty context.

解法与评估依据：The answer accepts the orthopedic service code and order fields but blocks signing because the Recommendation SBAR section is blank.

评分点：
- SP001 (1): Correct request and patient identifiers.
- SP002 (3): Correct service code, specialty, status, and priority.
- SP003 (3): Correct SBAR section completeness.
- SP004 (2): Correct linked chart evidence encounter.
- SP005 (2): Correct laterality consistency decision.
- SP006 (2): Correct ready-to-sign boolean.
- SP007 (2): Correct blocker code list.

迁移设计：As a train task, it teaches order-field validation, SBAR section interpretation, evidence linking, and ready-to-sign blockers.

构造记录：作者 Codex；创建日期 2026-07-07；更新日期 2026-07-07。主要变更：基于共享生成环境和精确匹配评估器完成初版任务构造。
