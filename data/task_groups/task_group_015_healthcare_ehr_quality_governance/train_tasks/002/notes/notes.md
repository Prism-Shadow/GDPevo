# train_002 Hidden Construction Notes

## English

Data/source lineage: This task is derived from scenario `SCN_015_healthcare_ehr_quality_governance` and source examples E005. It uses the shared EHR quality API generated under `env/` plus task-local payloads in `input/payloads/`.

Task definition: The solver audits a monthly orthopedic referral batch for code validity, laterality, duplicates, missing documents, authorization gaps, and triage priority.

Scenario fit: The task belongs to healthcare EHR data governance because it requires record-state reasoning, quality-control decisions, source reconciliation, and auditable structured output rather than casual text generation.

Material map: The batch endpoint supplies referral rows; the ICD-10 endpoint supplies code descriptions and musculoskeletal tracking membership; provider fields supply contact context.

Solution and evaluation basis: The answer exact-matches issue ID sets, corrected code suggestions, duplicate groups, anomaly distinctions, counts, and queue assignments.

Scoring goals:
- SP001 (2): Correct out-of-range ICD-10 referral IDs.
- SP002 (3): Correct laterality mismatch referral IDs.
- SP003 (2): Correct narrative/code mismatch referral IDs and correction for bursitis.
- SP004 (2): Correct duplicate referral group.
- SP005 (2): Correct shared-insurance anomaly distinction.
- SP006 (1): Correct missing records, imaging, and authorization counts.
- SP007 (3): Correct Tier 1 immediate queue.
- SP008 (1): Correct administrative reschedule queue.

Transfer design: As a train task, it anchors M00-M99 tracking, laterality checking, duplicate grouping by demographics, insurance anomaly handling, and tier synthesis.

Construction record: Author Codex; created 2026-07-07; updated 2026-07-07. Major changes: initial task construction with shared generated environment and exact-match evaluator.

## Chinese

数据来源：本任务来自场景 `SCN_015_healthcare_ehr_quality_governance` 和示例 E005。任务使用 `env/` 中生成的共享 EHR 质量管理 API，以及 `input/payloads/` 中的本任务可见材料。

任务定义：The solver audits a monthly orthopedic referral batch for code validity, laterality, duplicates, missing documents, authorization gaps, and triage priority.

场景适配：本任务属于医疗 EHR 数据治理，因为它要求判断病历状态、核对质量问题、协调多个来源，并输出可审计的结构化结果，而不是生成自由文本。

材料地图：The batch endpoint supplies referral rows; the ICD-10 endpoint supplies code descriptions and musculoskeletal tracking membership; provider fields supply contact context.

解法与评估依据：The answer exact-matches issue ID sets, corrected code suggestions, duplicate groups, anomaly distinctions, counts, and queue assignments.

评分点：
- SP001 (2): Correct out-of-range ICD-10 referral IDs.
- SP002 (3): Correct laterality mismatch referral IDs.
- SP003 (2): Correct narrative/code mismatch referral IDs and correction for bursitis.
- SP004 (2): Correct duplicate referral group.
- SP005 (2): Correct shared-insurance anomaly distinction.
- SP006 (1): Correct missing records, imaging, and authorization counts.
- SP007 (3): Correct Tier 1 immediate queue.
- SP008 (1): Correct administrative reschedule queue.

迁移设计：As a train task, it anchors M00-M99 tracking, laterality checking, duplicate grouping by demographics, insurance anomaly handling, and tier synthesis.

构造记录：作者 Codex；创建日期 2026-07-07；更新日期 2026-07-07。主要变更：基于共享生成环境和精确匹配评估器完成初版任务构造。
