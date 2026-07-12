# test_004 Hidden Construction Notes

## English

Data/source lineage: This task is derived from scenario `SCN_015_healthcare_ehr_quality_governance` and source examples E004, E005. It uses the shared EHR quality API generated under `env/` plus task-local payloads in `input/payloads/`.

Task definition: The solver validates a stat orthopedic service request where SBAR is present but laterality and oncology coordination create signing blockers.

Scenario fit: The task belongs to healthcare EHR data governance because it requires record-state reasoning, quality-control decisions, source reconciliation, and auditable structured output rather than casual text generation.

Material map: The service-request endpoint gives structured order fields and note text; linked encounter and codebook data identify the left-femur condition and right-code mismatch.

Solution and evaluation basis: The answer exact-matches order fields, laterality correction, SBAR presence, oncology flag, evidence, and signing blockers.

Scoring goals:
- SP001 (3): Correct order patient, service code, specialty, status, priority, and occurrence time.
- SP002 (3): Correct laterality correction.
- SP003 (3): Correct SBAR section completeness.
- SP004 (2): Correct oncology coordination requirement.
- SP005 (2): Correct linked chart evidence.
- SP006 (2): Correct ready-to-sign boolean.
- SP007 (2): Correct blocker codes.
- SP008 (1): Correct request identifier.

Transfer design: Transfer anchors are train_004 and train_002: SBAR/order checks transfer from service-request validation and laterality/oncology escalation transfers from referral audit.

Construction record: Author Codex; created 2026-07-07; updated 2026-07-07. Major changes: initial task construction with shared generated environment and exact-match evaluator.

## Chinese

数据来源：本任务来自场景 `SCN_015_healthcare_ehr_quality_governance` 和示例 E004, E005。任务使用 `env/` 中生成的共享 EHR 质量管理 API，以及 `input/payloads/` 中的本任务可见材料。

任务定义：The solver validates a stat orthopedic service request where SBAR is present but laterality and oncology coordination create signing blockers.

场景适配：本任务属于医疗 EHR 数据治理，因为它要求判断病历状态、核对质量问题、协调多个来源，并输出可审计的结构化结果，而不是生成自由文本。

材料地图：The service-request endpoint gives structured order fields and note text; linked encounter and codebook data identify the left-femur condition and right-code mismatch.

解法与评估依据：The answer exact-matches order fields, laterality correction, SBAR presence, oncology flag, evidence, and signing blockers.

评分点：
- SP001 (3): Correct order patient, service code, specialty, status, priority, and occurrence time.
- SP002 (3): Correct laterality correction.
- SP003 (3): Correct SBAR section completeness.
- SP004 (2): Correct oncology coordination requirement.
- SP005 (2): Correct linked chart evidence.
- SP006 (2): Correct ready-to-sign boolean.
- SP007 (2): Correct blocker codes.
- SP008 (1): Correct request identifier.

迁移设计：Transfer anchors are train_004 and train_002: SBAR/order checks transfer from service-request validation and laterality/oncology escalation transfers from referral audit.

构造记录：作者 Codex；创建日期 2026-07-07；更新日期 2026-07-07。主要变更：基于共享生成环境和精确匹配评估器完成初版任务构造。
