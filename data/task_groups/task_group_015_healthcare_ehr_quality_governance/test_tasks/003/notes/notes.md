# test_003 Hidden Construction Notes

## English

Data/source lineage: This task is derived from scenario `SCN_015_healthcare_ehr_quality_governance` and source examples E003. It uses the shared EHR quality API generated under `env/` plus task-local payloads in `input/payloads/`.

Task definition: The solver reviews an orthopedic post-acute handoff packet, checking active chart coverage, recency, stale exclusions, disclosure, and receiving facility alignment.

Scenario fit: The task belongs to healthcare EHR data governance because it requires record-state reasoning, quality-control decisions, source reconciliation, and auditable structured output rather than casual text generation.

Material map: The packet endpoint supplies draft sections; patient endpoints supply active lists, encounters, immunizations, and disclosures.

Solution and evaluation basis: The answer requires excluding inactive source items while recognizing that all required current packet categories are present.

Scoring goals:
- SP001 (3): Correct active problem code set.
- SP002 (2): Correct active medication and allergy coverage.
- SP003 (2): Correct four most recent encounter IDs.
- SP004 (1): Correct most recent immunization.
- SP005 (2): Correct stale/inactive item exclusions.
- SP006 (2): Correct disclosure status.
- SP007 (1): Correct receiving facility match.
- SP008 (2): Correct readiness status.

Transfer design: Transfer anchors are train_003 and train_005: active-only filtering, recency selection, disclosure readiness, and safety-oriented packet review recur with a new clinical context.

Construction record: Author Codex; created 2026-07-07; updated 2026-07-07. Major changes: initial task construction with shared generated environment and exact-match evaluator.

## Chinese

数据来源：本任务来自场景 `SCN_015_healthcare_ehr_quality_governance` 和示例 E003。任务使用 `env/` 中生成的共享 EHR 质量管理 API，以及 `input/payloads/` 中的本任务可见材料。

任务定义：The solver reviews an orthopedic post-acute handoff packet, checking active chart coverage, recency, stale exclusions, disclosure, and receiving facility alignment.

场景适配：本任务属于医疗 EHR 数据治理，因为它要求判断病历状态、核对质量问题、协调多个来源，并输出可审计的结构化结果，而不是生成自由文本。

材料地图：The packet endpoint supplies draft sections; patient endpoints supply active lists, encounters, immunizations, and disclosures.

解法与评估依据：The answer requires excluding inactive source items while recognizing that all required current packet categories are present.

评分点：
- SP001 (3): Correct active problem code set.
- SP002 (2): Correct active medication and allergy coverage.
- SP003 (2): Correct four most recent encounter IDs.
- SP004 (1): Correct most recent immunization.
- SP005 (2): Correct stale/inactive item exclusions.
- SP006 (2): Correct disclosure status.
- SP007 (1): Correct receiving facility match.
- SP008 (2): Correct readiness status.

迁移设计：Transfer anchors are train_003 and train_005: active-only filtering, recency selection, disclosure readiness, and safety-oriented packet review recur with a new clinical context.

构造记录：作者 Codex；创建日期 2026-07-07；更新日期 2026-07-07。主要变更：基于共享生成环境和精确匹配评估器完成初版任务构造。
