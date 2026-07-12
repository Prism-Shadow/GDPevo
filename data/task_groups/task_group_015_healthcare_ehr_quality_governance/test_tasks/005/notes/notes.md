# test_005 Hidden Construction Notes

## English

Data/source lineage: This task is derived from scenario `SCN_015_healthcare_ehr_quality_governance` and source examples E001, E002, E005. It uses the shared EHR quality API generated under `env/` plus task-local payloads in `input/payloads/`.

Task definition: The solver reviews an integrated queue spanning duplicate consolidation, referral quality, chart update, missing records, and contact actions.

Scenario fit: The task belongs to healthcare EHR data governance because it requires record-state reasoning, quality-control decisions, source reconciliation, and auditable structured output rather than casual text generation.

Material map: The queue document gives only target IDs; the solver must use patient, duplicate, referral, provider, codebook, disclosure, and audit endpoints to assemble the plan.

Solution and evaluation basis: The answer combines duplicate clarification, laterality/oncology contact, insurance anomaly contact, cardiology referral readiness, records request, tiering, and counts.

Scoring goals:
- SP001 (3): Correct duplicate consolidation decision.
- SP002 (3): Correct contact queue with recipient, fax, and reason codes.
- SP003 (2): Correct chart update decisions.
- SP004 (2): Correct records request list.
- SP005 (3): Correct tier assignments.
- SP006 (2): Correct insurance anomaly.
- SP007 (1): Correct reschedule administrative handling.
- SP008 (1): Correct summary counts.
- SP009 (2): Correct final queue status.

Transfer design: Transfer anchors are train_001, train_002, and train_005. The test mixes known conventions but still requires new cross-object exploration.

Construction record: Author Codex; created 2026-07-07; updated 2026-07-07. Major changes: initial task construction with shared generated environment and exact-match evaluator.

## Chinese

数据来源：本任务来自场景 `SCN_015_healthcare_ehr_quality_governance` 和示例 E001, E002, E005。任务使用 `env/` 中生成的共享 EHR 质量管理 API，以及 `input/payloads/` 中的本任务可见材料。

任务定义：The solver reviews an integrated queue spanning duplicate consolidation, referral quality, chart update, missing records, and contact actions.

场景适配：本任务属于医疗 EHR 数据治理，因为它要求判断病历状态、核对质量问题、协调多个来源，并输出可审计的结构化结果，而不是生成自由文本。

材料地图：The queue document gives only target IDs; the solver must use patient, duplicate, referral, provider, codebook, disclosure, and audit endpoints to assemble the plan.

解法与评估依据：The answer combines duplicate clarification, laterality/oncology contact, insurance anomaly contact, cardiology referral readiness, records request, tiering, and counts.

评分点：
- SP001 (3): Correct duplicate consolidation decision.
- SP002 (3): Correct contact queue with recipient, fax, and reason codes.
- SP003 (2): Correct chart update decisions.
- SP004 (2): Correct records request list.
- SP005 (3): Correct tier assignments.
- SP006 (2): Correct insurance anomaly.
- SP007 (1): Correct reschedule administrative handling.
- SP008 (1): Correct summary counts.
- SP009 (2): Correct final queue status.

迁移设计：Transfer anchors are train_001, train_002, and train_005. The test mixes known conventions but still requires new cross-object exploration.

构造记录：作者 Codex；创建日期 2026-07-07；更新日期 2026-07-07。主要变更：基于共享生成环境和精确匹配评估器完成初版任务构造。
