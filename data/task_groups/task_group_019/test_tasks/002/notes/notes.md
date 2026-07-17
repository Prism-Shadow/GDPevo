# test_002 Notes

## English

### Data and Source Lineage

This task belongs to `task_group_019`, scenario `SCN_019_regulatory_licensing_eligibility_and_compliance_review`, with source-example lineage from `E001`, `E002`, and especially `E003`. It uses the shared Cascadia Licensing Review Portal (CLRP) environment under `task_group/task_group_019/env/`.

The task-builder brief is the renewal manual-review queue for release batch `RV-2026-SUMMER` with release boundary `2026-07-15`. The generated data anchors for this batch are listed in `env/data/public_manifest.json` and `env/data/construction_manifest.json`, while the actual standard answer is derived from the generated `renewal_licensees` and `renewal_violations` records.

Solver-visible materials are:

- `input/prompt.txt`, which gives the base URL placeholder `http://localhost:<PORT>`, release batch `RV-2026-SUMMER`, and boundary date `2026-07-15`.
- `input/payloads/answer_template.json`, which defines the required JSON schema, rank ordering, controlled enum values, summary fields, and integer/date expectations.

The relevant CLRP public surfaces are:

- `GET /api/renewals/licensees?release_batch=RV-2026-SUMMER` for the current roster.
- `GET /exports/renewal_roster_RV-2026-SUMMER.csv` for the current roster export.
- `GET /api/renewals/violations?city=...` for city-scoped violation history.
- `GET /api/search/address?address=...` for address-level cross-checking.

### Task Definition and Scenario Fit

The business task is a pre-release renewal review screen. Staff need a ranked queue of exactly 12 current summer-batch licensees whose pre-boundary violation histories require manual review. The output is not a prose memo; it is a structured queue with stable IDs, match confidence, evidence-window counts, most recent usable evidence date, a controlled next-step label, a structured top-risk summary, and a count of matched post-boundary rows that were excluded.

The task fits the source renewal-queue example because it requires joining a current roster to noisy violation history, handling exact and close name matches, preserving shared-address uncertainty, applying a release-date boundary, and emitting reviewer-ready labels.

### Material Map

`renewal_licensees` supplies the current `RV-2026-SUMMER` roster, facility names, addresses, cities, statuses, license types, and successor hints. `renewal_violations` supplies historical violation rows by facility or close alias. The roster export is a public alternative to the API. The address search endpoint is useful for checking whether an address-level hit should be used for the named current licensee or treated as shared-address manual review.

The generated summer batch includes exact matches such as `Maple Kitchen 061`, close histories such as `Signal Lounge 098 Formerly`, post-boundary drift rows after `2026-07-15`, and the shared-address/manual case `Civic House 053`.

### Solution and Evaluation Basis

Current licensees are rows in `renewal_licensees` with `release_batch = 'RV-2026-SUMMER'`. Usable violation rows must match the current licensee by city and normalized address, then by exact facility name, supported close alias, or shared-address manual judgment. Address normalization treats `Suite B, ` as the same service address only when the name evidence supports the current licensee or when the row is deliberately retained as a shared-address manual case.

Rows with `violation_date > 2026-07-15` are not used for ranking, `violation_count_used`, or `most_recent_date_used`. They are counted in top-level `excluded_post_boundary_count`. The matched post-boundary exclusion count across the current summer roster is `23`.

The standard queue is:

1. `LIC-RV-2026-0061` Maple Kitchen 061
2. `LIC-RV-2026-0056` Crescent House 056
3. `LIC-RV-2026-0055` Pier House 055
4. `LIC-RV-2026-0089` Civic Bottle 089
5. `LIC-RV-2026-0096` Blue Lounge 096
6. `LIC-RV-2026-0063` Copper Kitchen 063
7. `LIC-RV-2026-0098` Signal Lounge 098
8. `LIC-RV-2026-0081` Urban Tap 081
9. `LIC-RV-2026-0085` Maple Bottle 085
10. `LIC-RV-2026-0065` Civic Kitchen 065
11. `LIC-RV-2026-0067` Pier Kitchen 067
12. `LIC-RV-2026-0053` Civic House 053

The queue emphasizes board-sanction, suspension, severe conduct, high-risk minor service, fine-collection burden, close continuity, post-boundary exclusion discipline, and a shared-address/manual review case. `Civic House 053` is retained as `shared_address_manual` because the usable history includes an unhinted close-name address hit at a shared-address anchor and should not be treated as a clean exact continuity case.

The evaluator has 8 exact-match scoring points with raw weights:

- `SP001`, weight 2: exact queue membership and current roster facility names.
- `SP002`, weight 2: ranks 1-5 in exact order.
- `SP003`, weight 2: ranks 6-12 in exact order.
- `SP004`, weight 2: all match-confidence enum values.
- `SP005`, weight 2: all pre-boundary violation counts.
- `SP006`, weight 1: all most-recent usable evidence dates.
- `SP007`, weight 2: all next-step labels.
- `SP008`, weight 3: `top_risk_summary` and `excluded_post_boundary_count`.

Likely model pitfalls include using post-boundary rows in ranking, missing close aliases, over-spreading shared-address history, ranking only the manifest anchors, ignoring high-risk distractors outside the first 12 IDs, counting rows from the wrong city, and writing narrative summaries instead of the controlled JSON schema.

### Transfer Design

This test transfers directly from `train_003`. The train task teaches the renewal-family conventions through answer comparison: start from the current release roster, match violations conservatively by name and address, accept close histories only with address support, avoid spreading shared-address rows, exclude post-boundary violations while counting them, rank the manual-review queue by pre-boundary risk, and use controlled enum labels. In this test, the same conventions apply to a larger summer queue with new entities, a later boundary date, more post-boundary drift, and an explicit shared-address/manual result.

Transfer-dependent scoring points are `SP001`, `SP003`, `SP004`, `SP005`, `SP007`, and `SP008`. `SP002` also benefits from train-derived ranking habits but depends heavily on summer-specific evidence exploration. `SP006` is mostly data-exploration dependent.

### Construction Record

Author: task-builder subagent for `test_002`, GPT-5.5 xhigh.
Created: 2026-07-07.
Updated: 2026-07-07.
Major changes: initial construction of prompt, answer template, standard answer, evaluator, and bilingual notes.

## 中文

### 数据与来源

本任务属于 `task_group_019`，场景为 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，来源样例包括 `E001`、`E002`，尤其对应 `E003` 的续期人工复核队列工作。任务使用共享的 Cascadia Licensing Review Portal（CLRP）环境，环境文件位于 `task_group/task_group_019/env/`。

任务构造要求是为发布批次 `RV-2026-SUMMER`、发布边界日期 `2026-07-15` 建立续期人工复核队列。该批次的生成锚点记录在 `env/data/public_manifest.json` 和 `env/data/construction_manifest.json` 中，标准答案则依据生成数据库中的 `renewal_licensees` 和 `renewal_violations` 记录构造。

求解者可见材料包括：

- `input/prompt.txt`：给出基础 URL 占位符 `http://localhost:<PORT>`、发布批次 `RV-2026-SUMMER` 和边界日期 `2026-07-15`。
- `input/payloads/answer_template.json`：定义输出 JSON 结构、排名顺序、枚举值、汇总字段以及整数和日期格式要求。

主要使用的 CLRP 公开入口包括当前续期花名册 API、该批次花名册导出、按城市查询的违规历史 API，以及地址搜索 API。

### 任务定义与场景适配

该任务模拟发布前续期人工复核筛选。工作人员需要从夏季批次的当前持证人中排出 12 个需要人工复核的对象。输出不是叙述性备忘录，而是结构化队列，包含稳定 ID、匹配置信度、证据窗口内的违规计数、最近可用证据日期、受控下一步标签、结构化风险摘要，以及被边界日期排除的后置违规记录数量。

本任务符合源样例的续期队列场景，因为它要求把当前花名册与噪声较多的历史违规记录关联，处理精确和近似名称匹配，保留共享地址不确定性，应用发布边界日期，并输出可由审核人员直接使用的标签。

### 材料地图

`renewal_licensees` 表提供 `RV-2026-SUMMER` 当前花名册、机构名称、地址、城市、状态、许可类型和继承提示。`renewal_violations` 表提供以机构名或近似别名记录的历史违规。花名册导出是 API 的公开替代来源。地址搜索入口用于判断地址层面的命中是否应归入当前持证人，或是否应保留为共享地址人工复核。

夏季批次中包含精确匹配，例如 `Maple Kitchen 061`；近似历史名称，例如 `Signal Lounge 098 Formerly`；`2026-07-15` 之后的后置漂移记录；以及共享地址人工复核案例 `Civic House 053`。

### 解题与评价依据

当前持证人是 `renewal_licensees` 表中 `release_batch = 'RV-2026-SUMMER'` 的记录。可使用的违规记录必须先按城市和规范化地址匹配，再根据当前机构名称、受支持近似别名或共享地址人工判断进行归属。地址规范化只在名称证据支持当前持证人，或该记录被明确保留为共享地址人工案例时，才把 `Suite B, ` 视为同一服务地址。

`violation_date > 2026-07-15` 的记录不参与排序、`violation_count_used` 或 `most_recent_date_used`，但要计入顶层字段 `excluded_post_boundary_count`。夏季当前花名册中，匹配但被边界排除的后置记录总数为 `23`。

标准队列依次为 `LIC-RV-2026-0061`、`LIC-RV-2026-0056`、`LIC-RV-2026-0055`、`LIC-RV-2026-0089`、`LIC-RV-2026-0096`、`LIC-RV-2026-0063`、`LIC-RV-2026-0098`、`LIC-RV-2026-0081`、`LIC-RV-2026-0085`、`LIC-RV-2026-0065`、`LIC-RV-2026-0067`、`LIC-RV-2026-0053`。

该队列重点覆盖董事会制裁、暂停、严重行为、高风险未成年人服务、罚款征收负担、近似名称连续性、后置记录排除，以及一个共享地址人工复核案例。`Civic House 053` 被标为 `shared_address_manual`，因为其可用历史包含共享地址锚点上的无继承提示近似名称命中，不能当成普通精确连续经营处理。

评估器包含 8 个精确匹配评分点，原始权重分别为 2、2、2、2、2、1、2、3。评分内容覆盖队列成员和当前花名册名称、前五名顺序、第六到第十二名顺序、匹配置信度、违规计数、最近可用日期、下一步标签，以及风险摘要和边界排除数量。

常见错误包括：把边界日期之后的违规记录用于排序；漏掉近似别名；把共享地址历史扩散给不应归属的持证人；只排名 manifest 中的锚点；忽略前 12 个 ID 之外的高风险干扰记录；混入错误城市的记录；或者输出自由文本而不是受控 JSON 结构。

### 迁移设计

本测试任务直接迁移自 `train_003`。训练任务在对照答案后应让模型学到续期类任务的规则：从当前发布批次花名册出发，保守匹配名称和地址，只有地址支持时才接受近似历史，不扩散共享地址记录，排除但统计边界后的违规记录，按边界前风险排序，并使用固定枚举标签。本测试把同一规则应用到新的夏季实体、更晚的边界日期、更多后置漂移记录，以及一个明确的共享地址人工复核结果上。

依赖迁移的评分点包括 `SP001`、`SP003`、`SP004`、`SP005`、`SP007` 和 `SP008`。`SP002` 也受训练中排序经验帮助，但更依赖夏季批次的具体证据探索。`SP006` 主要依赖任务内数据探索。

### 构造记录

作者：`test_002` task-builder subagent，GPT-5.5 xhigh。
创建日期：2026-07-07。
更新日期：2026-07-07。
主要变更：首次创建提示词、答案模板、标准答案、评估器和双语说明。
