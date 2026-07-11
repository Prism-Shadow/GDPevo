# train_001 Notes - CRM Contact Import Audit

## English

### Data and source lineage

This task belongs to `task_group_021`, scenario `SCN_021_data_cleaning_quality_pipeline`, with source examples `E001`, `E002`, and `E003`. The task implements the train builder brief for auditing CRM contact import batch `spring_summit_2026` before analytics load.

The authoritative data comes from the shared environment file `env/data/asterops_data.json`, served through `/api/crm/contact_rows`, `/api/reference/quality_rules`, `/api/catalog`, and `/downloads/crm_contact_rows_export.csv`. The batch has eight CRM source rows: `CR_SPR_001` through `CR_SPR_008`. No task-local data dump is provided; the visible prompt points solvers to `<TASK_ENV_BASE_URL>`, and `input/payloads/answer_template.json` defines the required output schema.

### Task definition and scenario fit

The business goal is to convert a dirty CRM import batch into a deterministic audit summary. The solver must identify duplicate `person_key` groups, suppress source rows with `contact_status = do_not_contact` or `consent_status = revoked`, drop canonical people with no reachable channel, normalize email and phone fields, select canonical contact decisions, and summarize retained contacts by city.

This matches the group scenario because it is a data-quality pipeline task over business records rather than a pure extraction task. It exercises entity reconciliation, controlled enums, source conflict handling, row suppression, normalization, and exact structured reporting.

### Material map

- `input/prompt.txt`: solver-visible business request for `spring_summit_2026`.
- `input/payloads/answer_template.json`: solver-visible schema, enum, ordering, and precision rules.
- `env/data/asterops_data.json`: hidden construction source for all authoritative CRM rows and rules.
- `/api/crm/contact_rows?batch_id=spring_summit_2026`: intended runtime source for target CRM rows.
- `/api/reference/quality_rules?domain=crm`: controlled CRM values for source systems and status fields.
- `/downloads/crm_contact_rows_export.csv`: shared CSV alternative to the API.
- `output/answer.json`: standard answer.
- `eval/evaluate.py` and `eval/eval.sh`: exact-match evaluator.

### Solution and evaluation basis

Canonical person groups in the target batch are `P_SPR_001`, `P_SPR_003`, `P_SPR_004`, `P_SPR_005`, and `P_SPR_006`. Duplicate groups are `P_SPR_001` and `P_SPR_004`, so `duplicate_group_count` is `2`. Rows `CR_SPR_004` and `CR_SPR_005` are suppressed source rows because one is do-not-contact and the other has revoked consent. `P_SPR_003` is dropped unreachable because both email and phone are empty.

Retained canonical contacts are:

- `P_SPR_001`: `crm_verified`, `opted@example.com`, `3125550144`, Austin.
- `P_SPR_004`: `steward_override`, `case@example.com`, `13125550166`, Austin.
- `P_SPR_006`: `partner_roster`, `fresh@example.com`, `3125550155`, Austin.

`P_SPR_005` remains a suppressed canonical decision, and `P_SPR_003` remains a dropped-unreachable canonical decision. The retained city summary is `{"Austin": 3}`.

Quality flags are exact source-row issue counts: raw rows `8`, canonical people `5`, duplicate person groups `2`, duplicate source rows beyond the first in duplicate groups `3`, missing-channel rows `1`, suppression rows `2`, email-normalization rows `3`, phone-normalization rows `5`, and stale or inactive rows `1`. `source_lineage_audit` records the duplicate-group source rows, selected canonical row, and noncanonical rows: `P_SPR_001` is a source-precedence override over the newer event row, and `P_SPR_004` is an active steward correction over an inactive row.

The evaluator uses eight scoring points with raw weights totaling `18`:

1. `batch_and_retained_count`, weight `1`.
2. `unreachable_drop_count`, weight `2`.
3. `duplicate_group_count`, weight `3`, including `source_lineage_audit`.
4. `suppressed_source_rows`, weight `2`.
5. `canonical_status_and_source`, weight `3`.
6. `canonical_normalized_channels`, weight `2`.
7. `retained_city_counts`, weight `2`.
8. `quality_flag_counts`, weight `3`.

Exact-match normalization sorts source-row ID lists, sorts `source_lineage_audit` and canonical contacts by `person_key`, lowercases and trims email values, strips non-digits from `phone_digits`, sorts city-count keys, and coerces count-like numeric values to integers. Likely model pitfalls are trusting a stale or partial export, treating every source row as a retained contact, counting suppressed source rows as suppressed people only, ignoring the corrected steward override for `P_SPR_004`, dropping the country-code digit from `+1-312-555-0166` despite the template rule, or counting raw duplicate rows instead of duplicate person groups.

### Transfer design

As a train task, `train_001` teaches through answer comparison rather than through the prompt. It anchors the CRM/contact reconciliation family for later tasks: use the shared environment as authoritative, group by stable `person_key`, separate raw source-row suppression from canonical person retention, apply deterministic email and phone normalization, count duplicate groups rather than merely duplicate rows, preserve source-lineage audit rows for duplicate groups, and keep retained-contact summaries separate from all canonical decisions. These conventions transfer directly to `train_004`, `test_001`, and the CRM portion of `test_004`.

### Construction record

Author: task-builder subagent for `train_001`.
Created: 2026-07-07.
Updated: 2026-07-07.
Major changes: Created solver prompt, answer template, standard answer, exact-match evaluator, and bilingual construction notes for `spring_summit_2026`.

## 中文

### 数据与来源

本任务属于 `task_group_021`，场景为 `SCN_021_data_cleaning_quality_pipeline`，来源样例为 `E001`、`E002` 和 `E003`。任务实现 `train_001` 的设计简报：在分析系统加载前审计 CRM 联系人导入批次 `spring_summit_2026`。

权威数据来自共享环境文件 `env/data/asterops_data.json`，运行时通过 `/api/crm/contact_rows`、`/api/reference/quality_rules`、`/api/catalog` 和 `/downloads/crm_contact_rows_export.csv` 暴露。该批次包含八条 CRM 源行：`CR_SPR_001` 到 `CR_SPR_008`。本任务没有提供任务本地的数据转储；可见提示只要求使用 `<TASK_ENV_BASE_URL>`，并用 `input/payloads/answer_template.json` 规定输出结构。

### 任务定义与场景匹配

业务目标是把脏 CRM 导入批次转换成确定性的审计摘要。求解者需要识别重复的 `person_key` 分组，排除 `contact_status = do_not_contact` 或 `consent_status = revoked` 的源行，丢弃没有可用邮箱和电话的规范联系人，规范化邮箱与电话，选择规范联系人决策，并按城市汇总保留联系人。

这符合本任务组的数据质量流水线场景，因为它不是简单抽取，而是围绕业务记录进行实体归并、受控枚举、来源冲突处理、行级抑制、字段规范化和精确结构化报告。

### 材料地图

- `input/prompt.txt`：面向求解者的 `spring_summit_2026` 业务请求。
- `input/payloads/answer_template.json`：面向求解者的输出结构、枚举、排序和精度规则。
- `env/data/asterops_data.json`：隐藏的构造依据，包含权威 CRM 行和规则。
- `/api/crm/contact_rows?batch_id=spring_summit_2026`：目标 CRM 行的预期运行时来源。
- `/api/reference/quality_rules?domain=crm`：CRM 来源系统和状态字段的受控取值。
- `/downloads/crm_contact_rows_export.csv`：共享 CSV 备选入口。
- `output/answer.json`：标准答案。
- `eval/evaluate.py` 和 `eval/eval.sh`：精确匹配评测器。

### 解法与评测依据

目标批次中的规范人员分组是 `P_SPR_001`、`P_SPR_003`、`P_SPR_004`、`P_SPR_005` 和 `P_SPR_006`。重复分组是 `P_SPR_001` 和 `P_SPR_004`，因此 `duplicate_group_count` 为 `2`。`CR_SPR_004` 和 `CR_SPR_005` 是被抑制的源行，原因分别是 do-not-contact 和 revoked consent。`P_SPR_003` 因邮箱和电话都为空而被判定为无法联系并丢弃。

保留的规范联系人为：

- `P_SPR_001`：`crm_verified`，`opted@example.com`，`3125550144`，Austin。
- `P_SPR_004`：`steward_override`，`case@example.com`，`13125550166`，Austin。
- `P_SPR_006`：`partner_roster`，`fresh@example.com`，`3125550155`，Austin。

`P_SPR_005` 保留为 suppressed 的规范决策，`P_SPR_003` 保留为 dropped_unreachable 的规范决策。保留联系人城市汇总为 `{"Austin": 3}`。

质量标记为精确的源行问题计数：原始行 `8`，规范人员 `5`，重复人员分组 `2`，重复分组中首条以外的源行 `3`，缺少联系渠道行 `1`，抑制行 `2`，邮箱规范化行 `3`，电话规范化行 `5`，过期或 inactive 行 `1`。`source_lineage_audit` 记录重复人员组的来源行、被选规范行和未选来源行：`P_SPR_001` 是来源优先级覆盖最新行，`P_SPR_004` 是 steward active 修正覆盖 inactive 行。

评测器使用八个评分点，原始权重总和为 `18`：

1. `batch_and_retained_count`，权重 `1`。
2. `unreachable_drop_count`，权重 `2`。
3. `duplicate_group_count`，权重 `3`，同时检查 `source_lineage_audit`。
4. `suppressed_source_rows`，权重 `2`。
5. `canonical_status_and_source`，权重 `3`。
6. `canonical_normalized_channels`，权重 `2`。
7. `retained_city_counts`，权重 `2`。
8. `quality_flag_counts`，权重 `3`。

精确匹配前的规范化包括：源行 ID 列表排序，`source_lineage_audit` 按 `person_key` 排序，规范联系人按 `person_key` 排序，邮箱去首尾空格并转小写，`phone_digits` 去除非数字字符，城市计数字段按键排序，以及将计数值转换为整数。常见错误包括信任过期或局部导出，把每条源行都当作保留联系人，只按人员而不是源行统计抑制项，忽略 `P_SPR_004` 的 steward 修正行，违反模板规则删除 `+1-312-555-0166` 的国家码数字，或把重复源行数误当作重复人员分组数。

### 迁移设计

作为训练任务，`train_001` 通过答案对比提供经验，而不是在提示中直接教学。它锚定 CRM 联系人归并任务族：共享环境是权威来源，按稳定的 `person_key` 分组，区分源行抑制与规范人员保留，执行确定性的邮箱和电话规范化，统计重复分组而不是简单统计重复行，并将保留联系人汇总与全部规范决策分开。这些约定会迁移到 `train_004`、`test_001` 以及 `test_004` 中的 CRM 部分。

### 构造记录

作者：`train_001` task-builder subagent。
创建日期：2026-07-07。
更新日期：2026-07-07。
主要变更：为 `spring_summit_2026` 创建了求解者提示、答案模板、标准答案、精确匹配评测器和双语构造说明。
## Rework addendum / 返工补充

English: After calibration rework, the train answer includes `decision_audit` and `source_lineage_audit` with concrete CRM evidence: source-precedence override person keys, duplicate-group source rows, suppressed-but-reachable source rows, and rows whose email or phone normalization changes the raw value. These business lists transfer to contact and partner test tasks as recoverable data results.

中文：校准返工后，训练答案在 `decision_audit` 和 `source_lineage_audit` 中加入了具体 CRM 证据：来源优先级覆盖的人员键、重复分组来源行、仍有联系方式但被抑制的来源行，以及邮箱或电话规范化改变原始值的行。这些业务列表可作为可恢复的数据结果迁移到联系人和伙伴测试任务。
