# train_003 Hidden Construction Notes

## English

Data/source lineage: This task is derived from scenario `SCN_015_healthcare_ehr_quality_governance` and source examples E003. It uses the shared EHR quality API generated under `env/` plus task-local payloads in `input/payloads/`.

Task definition: The solver reviews a care-transition packet and decides whether it has complete active chart coverage and required handoff sections.

Scenario fit: The task belongs to healthcare EHR data governance because it requires record-state reasoning, quality-control decisions, source reconciliation, and auditable structured output rather than casual text generation.

Material map: The packet endpoint provides draft sections; patient endpoints provide active chart lists, encounter recency, immunization history, and disclosure records.

Solution and evaluation basis: The answer uses active-only list filtering, the four most recent encounters, most recent immunization, and missing cognitive status as the readiness blocker.

Scoring goals:
- SP001 (3): Correct active problem code set.
- SP002 (2): Correct active medication and allergy coverage.
- SP003 (2): Correct four most recent encounter IDs.
- SP004 (1): Correct most recent immunization.
- SP005 (2): Correct missing packet section.
- SP006 (2): Correct disclosure status.
- SP007 (2): Correct handoff readiness.
- SP008 (1): Correct packet risk flags.

Transfer design: As a train task, it teaches active-versus-stale filtering, recency rules, handoff category coverage, and disclosure/readiness conventions.

Construction record: Author Codex; created 2026-07-07; updated 2026-07-07. Major changes: initial task construction with shared generated environment and exact-match evaluator.

## Chinese

数据来源：本任务来自场景 `SCN_015_healthcare_ehr_quality_governance` 和示例 E003。任务使用 `env/` 中生成的共享 EHR 质量管理 API，以及 `input/payloads/` 中的本任务可见材料。

任务定义：The solver reviews a care-transition packet and decides whether it has complete active chart coverage and required handoff sections.

场景适配：本任务属于医疗 EHR 数据治理，因为它要求判断病历状态、核对质量问题、协调多个来源，并输出可审计的结构化结果，而不是生成自由文本。

材料地图：The packet endpoint provides draft sections; patient endpoints provide active chart lists, encounter recency, immunization history, and disclosure records.

解法与评估依据：The answer uses active-only list filtering, the four most recent encounters, most recent immunization, and missing cognitive status as the readiness blocker.

评分点：
- SP001 (3): Correct active problem code set.
- SP002 (2): Correct active medication and allergy coverage.
- SP003 (2): Correct four most recent encounter IDs.
- SP004 (1): Correct most recent immunization.
- SP005 (2): Correct missing packet section.
- SP006 (2): Correct disclosure status.
- SP007 (2): Correct handoff readiness.
- SP008 (1): Correct packet risk flags.

迁移设计：As a train task, it teaches active-versus-stale filtering, recency rules, handoff category coverage, and disclosure/readiness conventions.

构造记录：作者 Codex；创建日期 2026-07-07；更新日期 2026-07-07。主要变更：基于共享生成环境和精确匹配评估器完成初版任务构造。
