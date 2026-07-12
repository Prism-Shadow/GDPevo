# test_001 Hidden Construction Notes

## English

Data/source lineage: This task is derived from scenario `SCN_015_healthcare_ehr_quality_governance` and source examples E001. It uses the shared EHR quality API generated under `env/` plus task-local payloads in `input/payloads/`.

Task definition: The solver audits a renal duplicate candidate with demographic conflict and determines that active facts can be reconciled but the merge is blocked pending clarification.

Scenario fit: The task belongs to healthcare EHR data governance because it requires record-state reasoning, quality-control decisions, source reconciliation, and auditable structured output rather than casual text generation.

Material map: Duplicate candidate, patient chart, disclosure, and audit-log endpoints supply the evidence; no task-specific answer endpoint exists.

Solution and evaluation basis: The answer transfers merge direction and active-list preservation but requires task-specific discovery of the address conflict and expired source disclosure.

Scoring goals:
- SP001 (3): Correct target/source and clarification disposition.
- SP002 (2): Correct active problem union.
- SP003 (2): Correct active medication union.
- SP004 (2): Correct active allergy union.
- SP005 (2): Correctly exclude inactive allergy item.
- SP006 (2): Correct audit event and blocked status.
- SP007 (2): Correct disclosure flag.
- SP008 (1): Correct follow-up contact action.

Transfer design: Test transfer anchors are train_001 and train_005: merge-source conventions, active-only filtering, and allergy safety all recur with new patient facts.

Construction record: Author Codex; created 2026-07-07; updated 2026-07-07. Major changes: initial task construction with shared generated environment and exact-match evaluator.

## Chinese

数据来源：本任务来自场景 `SCN_015_healthcare_ehr_quality_governance` 和示例 E001。任务使用 `env/` 中生成的共享 EHR 质量管理 API，以及 `input/payloads/` 中的本任务可见材料。

任务定义：The solver audits a renal duplicate candidate with demographic conflict and determines that active facts can be reconciled but the merge is blocked pending clarification.

场景适配：本任务属于医疗 EHR 数据治理，因为它要求判断病历状态、核对质量问题、协调多个来源，并输出可审计的结构化结果，而不是生成自由文本。

材料地图：Duplicate candidate, patient chart, disclosure, and audit-log endpoints supply the evidence; no task-specific answer endpoint exists.

解法与评估依据：The answer transfers merge direction and active-list preservation but requires task-specific discovery of the address conflict and expired source disclosure.

评分点：
- SP001 (3): Correct target/source and clarification disposition.
- SP002 (2): Correct active problem union.
- SP003 (2): Correct active medication union.
- SP004 (2): Correct active allergy union.
- SP005 (2): Correctly exclude inactive allergy item.
- SP006 (2): Correct audit event and blocked status.
- SP007 (2): Correct disclosure flag.
- SP008 (1): Correct follow-up contact action.

迁移设计：Test transfer anchors are train_001 and train_005: merge-source conventions, active-only filtering, and allergy safety all recur with new patient facts.

构造记录：作者 Codex；创建日期 2026-07-07；更新日期 2026-07-07。主要变更：基于共享生成环境和精确匹配评估器完成初版任务构造。
