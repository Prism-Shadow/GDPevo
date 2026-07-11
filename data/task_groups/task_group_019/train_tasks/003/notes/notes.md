# train_003 Notes

## English

### Data and Source Lineage

This task belongs to `task_group_019`, scenario `SCN_019_regulatory_licensing_eligibility_and_compliance_review`, with source-example lineage from `E001`, `E002`, and especially `E003`. It uses the shared Cascadia Licensing Review Portal (CLRP) environment generated under `task_group/task_group_019/env/`.

The solver-visible materials are:

- `input/prompt.txt`, which states the release batch `RV-2026-SPRING`, the release boundary `2026-04-15`, and the CLRP base URL placeholder `http://localhost:<PORT>`.
- `input/payloads/answer_template.json`, which defines the JSON schema, rank ordering, controlled enum values, and method flag requirements.

The relevant CLRP public surfaces are:

- `GET /api/renewals/licensees?release_batch=RV-2026-SPRING` for the current roster.
- `GET /exports/renewal_roster_RV-2026-SPRING.csv` as the public roster export.
- `GET /api/renewals/violations?city=...` for violation history in roster cities.
- `GET /api/search/address?address=...` for address-level cross-checks.

### Task Definition and Scenario Fit

The business task is a renewal manual-review screen before release. Staff must rank exactly 10 current licensees from the spring renewal batch using pre-release violation evidence, while excluding violation rows after the boundary date. The task mirrors the Montgomery renewal-queue source example: current roster reconciliation, violation-history matching, exact versus close-name decisions, shared-address caution, date-boundary handling, and controlled output labels.

This is a train task rather than a tutorial. It does not expose the matching or ranking rule in the prompt, but the hidden answer records a stable interpretation for review and scoring.

### Solution Basis

Current licensees are all rows in `renewal_licensees` with `release_batch = 'RV-2026-SPRING'`. Violation rows are considered usable when the city matches and the normalized address matches the roster address. Address normalization strips a leading `Suite B, ` only when the historical name still matches the current facility or a close alias; address-only matches are not spread to unrelated licensees.

Name confidence is:

- `exact`: all used rows match the current `facility_name`.
- `close`: at least one used row matches a supported close alias or `successor_hint`, with the same normalized address.
- `shared_address_manual`: allowed by the schema but not used in the standard queue.

Close aliases include the deterministic CLRP variants generated for the environment, such as `Grill` to `Grille`, `Market` to `Mkt`, `Cafe` to `Cafe and Bar`, `Room` to `Rm`, `House` to `Haus`, `Kitchen` to `Kitch`, and `Formerly` suffixes.

Rows with `violation_date > 2026-04-15` are excluded from ranking and counted in `method_flags.excluded_post_boundary_count`. The total matched post-boundary exclusion count across the spring roster is `10`.

The ranked queue is based on a manual-review risk screen using the matched pre-boundary rows. High-priority board items are driven by board-sanction, suspension, severe public-safety, minor-service, and high-severity histories. Fine-check items are driven by unpaid or material fine-collection rows. ALERT-check items are driven by repeated ALERT-related rows. Ties are resolved by the strength of matched history, violation count, severity/fine/ALERT burden, and recency.

The standard answer queue is:

1. `LIC-RV-2026-0004` Drift Grill 004
2. `LIC-RV-2026-0045` Urban Room 045
3. `LIC-RV-2026-0010` Depot Grill 010
4. `LIC-RV-2026-0043` Pier Room 043
5. `LIC-RV-2026-0035` Vista Cafe 035
6. `LIC-RV-2026-0042` Hearth Room 042
7. `LIC-RV-2026-0021` Urban Market 021
8. `LIC-RV-2026-0025` Maple Cafe 025
9. `LIC-RV-2026-0032` Crescent Cafe 032
10. `LIC-RV-2026-0019` Pier Market 019

### Evaluation Basis

The evaluator has 8 exact-match scoring points with raw weights:

- `queue_membership`, weight 2: exactly the expected 10 license IDs.
- `top_three_order`, weight 2: ranks 1-3 exactly.
- `ranks_four_to_ten_order`, weight 2: ranks 4-10 exactly.
- `match_confidence_values`, weight 1: all confidence values exactly match.
- `violation_counts`, weight 2: all used violation counts exactly match.
- `most_recent_dates`, weight 1: all most recent pre-boundary dates exactly match.
- `next_step_labels`, weight 2: all controlled labels exactly match.
- `method_flags`, weight 2: release batch, boundary date, queue size, post-boundary exclusion count, and boolean method flags exactly match.

The evaluator intentionally avoids prose matching and does not require whole-file equality.

Likely model pitfalls include using all violation rows after the release boundary, treating city-level rows as belonging to every same-city licensee, failing to include close-alias rows at the same address, spreading address-only or shared-address history, ranking only the first ten manifest anchors, or outputting prose labels instead of controlled enum values.

### Transfer Design

Solving this train task and comparing against the answer should teach the renewal-family conventions that transfer to `test_002` and the renewal portion of `test_005`: use the current release roster, match violation history conservatively by name and address, accept close matches only with address support, do not spread shared-address history without name support, exclude post-boundary violations from ranking while counting them, and emit controlled next-step labels rather than free-form narratives.

### Construction Record

Author: task-builder subagent for `train_003`, GPT-5.5 xhigh.  
Created: 2026-07-07.  
Updated: 2026-07-07.  
Major changes: initial task construction with prompt, answer template, standard answer, evaluator, and bilingual notes.

## 中文

### 数据与来源

本任务属于 `task_group_019`，场景为 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，来源样例包括 `E001`、`E002`，尤其对应 `E003` 的续期人工复核队列工作。任务使用共享的 Cascadia Licensing Review Portal（CLRP）环境，环境文件位于 `task_group/task_group_019/env/`。

求解者可见材料包括：

- `input/prompt.txt`：给出发布批次 `RV-2026-SPRING`、发布边界日期 `2026-04-15`，以及 CLRP 基础 URL 占位符 `http://localhost:<PORT>`。
- `input/payloads/answer_template.json`：定义 JSON 结构、排名顺序、枚举值和方法标志字段。

主要使用的 CLRP 公开入口包括续期持证人 API、该批次续期花名册导出、按城市查询的违规历史 API，以及地址搜索 API。

### 任务定义与场景适配

该任务模拟发布前续期人工复核筛选。工作人员需要从春季续期批次的当前持证人中选出并排序 10 个最需要人工复核的对象，同时排除边界日期之后的违规记录。它延续了源样例 `E003` 的核心难点：当前花名册与历史违规记录关联、精确和近似名称匹配、共享地址谨慎处理、日期边界过滤，以及结构化复核标签输出。

这是一个真实训练任务，不是教程。提示词不会公开具体匹配和排序规则，但隐藏答案与本说明记录了可复核的标准解释。

### 解题依据

当前持证人是 `renewal_licensees` 表中 `release_batch = 'RV-2026-SPRING'` 的所有记录。违规记录只有在城市一致且规范化地址与花名册地址一致时才可使用。地址规范化只在历史名称仍能匹配当前机构名称或受支持近似别名时去除开头的 `Suite B, `；不能把仅地址相似的记录扩散给无名称支持的持证人。

匹配置信度规则如下：

- `exact`：所有使用的记录均与当前 `facility_name` 精确匹配。
- `close`：至少一条使用的记录通过同一地址上的近似别名或 `successor_hint` 匹配。
- `shared_address_manual`：模板允许该枚举，但标准队列中未使用。

近似别名包括环境生成器中的确定性变体，例如 `Grill` 到 `Grille`、`Market` 到 `Mkt`、`Cafe` 到 `Cafe and Bar`、`Room` 到 `Rm`、`House` 到 `Haus`、`Kitchen` 到 `Kitch`，以及 `Formerly` 后缀。

`violation_date > 2026-04-15` 的记录不参与排序，但要计入 `method_flags.excluded_post_boundary_count`。春季批次当前花名册中，共有 `10` 条已匹配但被边界排除的后置记录。

标准队列基于发布前人工复核风险筛选。董事会复核优先由制裁、暂停、严重公共安全、未成年人服务和高严重度历史驱动；罚款复核由未缴或重要罚款记录驱动；ALERT 复核由重复 ALERT 相关记录驱动。并列时参考匹配历史强度、违规数量、严重度、罚款、ALERT 负担和最近日期。

### 评价依据

评估器包含 8 个精确匹配评分点，原始权重为 2、2、2、1、2、1、2、2。评分内容分别覆盖队列成员集合、前三名顺序、第四到第十名顺序、匹配置信度、违规计数、最近使用日期、下一步标签和方法标志。评估不使用自由文本质量判断，也不要求整文件完全相同。

常见错误包括：使用边界日期之后的违规记录参与排序；把同一城市的违规记录误归给所有持证人；忽略同一地址上的近似名称；扩散仅地址匹配的历史；只取 manifest 的前 10 个锚点；或输出非枚举的自由文本标签。

### 迁移设计

该训练任务用于让模型在对照答案后学习续期类任务的可迁移规则：先取当前发布批次花名册，保守匹配名称与地址，只有地址支持时才接受近似名称，不扩散共享地址历史，排除但统计边界后的违规记录，并使用固定枚举标签输出。这些经验会迁移到 `test_002` 和 `test_005` 中的续期复核部分。

### 构造记录

作者：`train_003` task-builder subagent，GPT-5.5 xhigh。  
创建日期：2026-07-07。  
更新日期：2026-07-07。  
主要变更：首次创建提示词、答案模板、标准答案、评估器和双语说明。
