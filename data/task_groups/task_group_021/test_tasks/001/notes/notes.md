# test_001 Notes - CRM Contact Import Audit

## English

### Data and source lineage

This task belongs to `task_group_021`, scenario `SCN_021_data_cleaning_quality_pipeline`, with source examples `E001`, `E002`, and `E003`. It implements the test builder brief for auditing CRM contact import batch `expo_followup_2026`.

The authoritative construction data is in `env/data/asterops_data.json`, exposed at runtime through `/api/crm/contact_rows`, `/api/reference/quality_rules`, `/api/catalog`, and `/downloads/crm_contact_rows_export.csv`. The target batch contains eight source rows: `CR_EXP_009` through `CR_EXP_016`. Solver-visible inputs are `input/prompt.txt` and `input/payloads/answer_template.json`; no task-local answer-like extract is provided.

### Task definition and scenario fit

The business task is to turn a dirty CRM import batch into a deterministic pre-load audit. The expected output identifies final retained people, unreachable drops, duplicate person groups, source-row suppression, source conflicts, canonical contact decisions, retained city/domain summaries, and quality flags.

This fits the task group because it is a data-quality pipeline workflow over operational CRM records. It requires entity grouping, canonical source selection, channel normalization, controlled status handling, conflict accounting, and exact structured reporting rather than prose explanation.

### Material map

- `input/prompt.txt`: solver-visible request for `expo_followup_2026` using `<TASK_ENV_BASE_URL>`.
- `input/payloads/answer_template.json`: solver-visible output schema, enums, ordering, and normalization expectations.
- `env/data/asterops_data.json`: hidden construction source for all target rows and quality-rule references.
- `/api/crm/contact_rows?batch_id=expo_followup_2026`: intended runtime source for target CRM rows.
- `/api/reference/quality_rules?domain=crm`: controlled CRM source, contact status, and consent values.
- `/downloads/crm_contact_rows_export.csv`: shared CSV fallback containing the same CRM row universe.
- `output/answer.json`: standard answer.
- `eval/evaluate.py` and `eval/eval.sh`: exact-match evaluator.

### Solution and evaluation basis

The target batch has five canonical person groups: `P_EXP_001`, `P_EXP_003`, `P_EXP_004`, `P_EXP_005`, and `P_EXP_006`. Duplicate groups are `P_EXP_001` and `P_EXP_004`, so `duplicate_group_count` is `2`. Suppressed source rows are `CR_EXP_012` because the row is do-not-contact and `CR_EXP_013` because consent is revoked. `P_EXP_003` is dropped unreachable because both email and phone are empty.

Retained canonical contacts are:

- `P_EXP_001`: `crm_verified`, `opted@example.com`, `3125550144`, Denver, domain `example.com`.
- `P_EXP_004`: `steward_override`, `case@example.com`, `13125550166`, Denver, domain `example.com`.
- `P_EXP_006`: `partner_roster`, `fresh@example.com`, `3125550155`, Denver, domain `example.com`.

`P_EXP_005` remains a suppressed canonical decision, and `P_EXP_003` remains a dropped-unreachable canonical decision. Retained city counts are `{"Denver": 3}` and retained domain counts are `{"example.com": 3}`. Source-conflict person keys are `P_EXP_001` and `P_EXP_004`; these groups contain multiple source systems and conflicting contact or consent attributes.

Quality flags are exact source-row issue counts: raw rows `8`, canonical people `5`, duplicate person groups `2`, duplicate source rows beyond the first in duplicate groups `3`, missing-channel rows `1`, suppression rows `2`, email-normalization rows `3`, phone-normalization rows `5`, stale or inactive rows `1`, source-conflict groups `2`, and source-conflict rows `5`. `source_lineage_audit` records the source-precedence override for `P_EXP_001` and the active steward correction for `P_EXP_004`.

The evaluator has eight scoring points with raw weights totaling `19`:

1. `transfer_train_001_train_004_retained_count`, weight `2`.
2. `transfer_train_001_blocked_and_unreachable`, weight `2`.
3. `transfer_train_001_duplicate_group_count`, weight `3`, including `source_lineage_audit`.
4. `task_specific_source_conflict_person_keys`, weight `2`.
5. `transfer_train_001_canonical_status_and_source`, weight `3`.
6. `transfer_train_001_canonical_normalized_channels`, weight `2`.
7. `transfer_train_004_task_specific_city_domain_counts`, weight `2`.
8. `mixed_quality_flag_counts`, weight `3`.

The evaluator exact-matches structured business results. It sorts ID-like lists, sorts `source_lineage_audit` and canonical contacts by `person_key`, lowercases emails and domains, strips non-digits from `phone_digits`, coerces count-like values to integers, and requires valid controlled enums for canonical source and contact status. Likely model pitfalls include treating raw rows as retained contacts, missing row-level suppression, counting duplicate rows instead of duplicate person groups, ignoring the `+1` country-code digit in the steward phone number, retaining the stale inactive event row for `P_EXP_004`, and counting blocked or dropped contacts in retained city/domain summaries.

### Transfer design

The hidden transfer anchors are `train_001` and `train_004`. From `train_001`, solvers should transfer the CRM batch reconciliation pattern: use the shared environment as authoritative, group by `person_key`, distinguish source-row suppression from canonical person decisions, normalize email and phone fields, select steward or verified canonical contacts when conflicts exist, count duplicate groups deterministically, and preserve source-lineage audit rows for duplicate groups. From `train_004`, solvers should transfer domain normalization and the habit of counting only retained canonical records in audience-style summaries.

Transfer-dependent scoring points are retained count, blocked/unreachable handling, duplicate group count and source lineage, canonical contact decisions, normalized channels, and retained city/domain counts. Task-specific exploration is still required for the `EXP` source rows, Denver retained-city summary, source-conflict person keys, and the conflict-related quality flags.

### Construction record

Author: task-builder subagent for `test_001`.
Created: 2026-07-07.
Updated: 2026-07-07.
Major changes: Created solver prompt, answer template, standard answer, exact-match evaluator, and bilingual notes for `expo_followup_2026`.

## 中文

### 数据与来源

本任务属于 `task_group_021`，场景为 `SCN_021_data_cleaning_quality_pipeline`，来源样例为 `E001`、`E002` 和 `E003`。任务实现 `test_001` 的设计简报：审计 CRM 联系人导入批次 `expo_followup_2026`。

权威构造数据位于 `env/data/asterops_data.json`，运行时通过 `/api/crm/contact_rows`、`/api/reference/quality_rules`、`/api/catalog` 和 `/downloads/crm_contact_rows_export.csv` 暴露。目标批次包含八条源行：`CR_EXP_009` 到 `CR_EXP_016`。求解者可见输入是 `input/prompt.txt` 和 `input/payloads/answer_template.json`；没有提供类似答案的任务本地抽取文件。

### 任务定义与场景匹配

业务任务是把脏 CRM 导入批次转换为确定性的加载前审计结果。预期输出需要识别最终保留人员、无法联系的丢弃项、重复人员分组、源行抑制、来源冲突、规范联系人决策、保留联系人的城市和域名汇总，以及质量标记。

这符合本任务组的数据质量流水线场景，因为它围绕运营 CRM 记录进行实体分组、规范来源选择、联系渠道规范化、受控状态处理、冲突计数和精确结构化报告，而不是生成解释性文本。

### 材料地图

- `input/prompt.txt`：使用 `<TASK_ENV_BASE_URL>` 的 `expo_followup_2026` 求解者可见请求。
- `input/payloads/answer_template.json`：求解者可见的输出结构、枚举、排序和规范化要求。
- `env/data/asterops_data.json`：隐藏构造来源，包含全部目标行和质量规则引用。
- `/api/crm/contact_rows?batch_id=expo_followup_2026`：目标 CRM 行的预期运行时入口。
- `/api/reference/quality_rules?domain=crm`：CRM 来源、联系人状态和同意状态的受控值。
- `/downloads/crm_contact_rows_export.csv`：包含同一 CRM 行全集的共享 CSV 备选入口。
- `output/answer.json`：标准答案。
- `eval/evaluate.py` 和 `eval/eval.sh`：精确匹配评测器。

### 解法与评测依据

目标批次有五个规范人员分组：`P_EXP_001`、`P_EXP_003`、`P_EXP_004`、`P_EXP_005` 和 `P_EXP_006`。重复分组是 `P_EXP_001` 和 `P_EXP_004`，因此 `duplicate_group_count` 为 `2`。被抑制的源行是 `CR_EXP_012` 和 `CR_EXP_013`，前者因为 do-not-contact，后者因为同意状态 revoked。`P_EXP_003` 因邮箱和电话都为空而被判定为无法联系并丢弃。

保留的规范联系人为：

- `P_EXP_001`：`crm_verified`，`opted@example.com`，`3125550144`，Denver，域名 `example.com`。
- `P_EXP_004`：`steward_override`，`case@example.com`，`13125550166`，Denver，域名 `example.com`。
- `P_EXP_006`：`partner_roster`，`fresh@example.com`，`3125550155`，Denver，域名 `example.com`。

`P_EXP_005` 保留为 suppressed 的规范决策，`P_EXP_003` 保留为 dropped-unreachable 的规范决策。保留城市计数为 `{"Denver": 3}`，保留域名计数为 `{"example.com": 3}`。来源冲突人员键是 `P_EXP_001` 和 `P_EXP_004`；这些分组包含多个来源系统，并且联系人或同意属性相互冲突。

质量标记为精确源行问题计数：原始行 `8`，规范人员 `5`，重复人员分组 `2`，重复分组中首条以外的源行 `3`，缺少联系渠道行 `1`，抑制行 `2`，邮箱规范化行 `3`，电话规范化行 `5`，过期或 inactive 行 `1`，来源冲突分组 `2`，来源冲突源行 `5`。`source_lineage_audit` 记录 `P_EXP_001` 的来源优先级覆盖和 `P_EXP_004` 的 steward active 修正。

评测器有八个评分点，原始权重总和为 `19`：

1. `transfer_train_001_train_004_retained_count`，权重 `2`。
2. `transfer_train_001_blocked_and_unreachable`，权重 `2`。
3. `transfer_train_001_duplicate_group_count`，权重 `3`，同时检查 `source_lineage_audit`。
4. `task_specific_source_conflict_person_keys`，权重 `2`。
5. `transfer_train_001_canonical_status_and_source`，权重 `3`。
6. `transfer_train_001_canonical_normalized_channels`，权重 `2`。
7. `transfer_train_004_task_specific_city_domain_counts`，权重 `2`。
8. `mixed_quality_flag_counts`，权重 `3`。

评测器对结构化业务结果做精确匹配。它会排序 ID 类列表，按 `person_key` 排序 `source_lineage_audit` 和规范联系人，将邮箱和域名转为小写，移除 `phone_digits` 中的非数字字符，将计数字段转为整数，并要求规范来源与联系人状态使用有效受控枚举。常见错误包括把原始行当作保留联系人，漏掉行级抑制，把重复源行数误当作重复人员分组数，忽略 steward 电话号码中的 `+1` 国家码数字，错误保留 `P_EXP_004` 的过期 inactive 活动行，以及把被阻止或丢弃的联系人计入保留城市或域名汇总。

### 迁移设计

隐藏迁移锚点是 `train_001` 和 `train_004`。从 `train_001` 可迁移 CRM 批次归并模式：以共享环境为权威来源，按 `person_key` 分组，区分源行抑制与规范人员决策，规范化邮箱和电话，在冲突中选择 steward 或 verified 规范联系人，并确定性地统计重复分组。从 `train_004` 可迁移域名规范化，以及只用保留的规范记录进行受众式汇总的习惯。

依赖迁移的评分点包括保留人数、阻止与无法联系处理、重复分组数、规范联系人决策、规范化联系渠道，以及保留城市和域名计数。任务自身仍要求探索 `EXP` 源行、Denver 保留城市汇总、来源冲突人员键和冲突相关质量标记。

### 构造记录

作者：`test_001` task-builder subagent。
创建日期：2026-07-07。
更新日期：2026-07-07。
主要变更：为 `expo_followup_2026` 创建了求解者提示、答案模板、标准答案、精确匹配评测器和双语说明。
## Rework addendum / 返工补充

English: The final evaluator binds several high-weight contact scoring points to `decision_audit` and `source_lineage_audit` business evidence: precedence overrides, duplicate-group source lineage, suppressed reachable source rows, and rows changed by channel normalization. These checks are anchored by `train_001` and reinforced by `train_004`; they are recoverable from the environment data.

中文：最终评测器将若干高权重联系人评分点绑定到 `decision_audit` 和 `source_lineage_audit` 的业务证据：来源优先级覆盖、重复分组来源脉络、仍可联系但被抑制的来源行，以及渠道规范化改变原始值的行。这些检查由 `train_001` 锚定并由 `train_004` 强化，且可从环境数据恢复。
