# test_004 Notes: Partner Onboarding Wave 2

## English

This task belongs to `task_group_021`, scenario `SCN_021_data_cleaning_quality_pipeline`, with source examples `E001`, `E002`, and `E003`. It implements the test task brief for `test_004`: normalize partner onboarding roster `partner_onboarding_wave2` and decide which contacts can enter the partner analytics table. The shared environment data comes from `env/data/asterops_data.json`, especially `crm_contact_rows`, `reference_category_aliases`, and `reference_quality_rules`. The task-local payload is `input/payloads/partner_onboarding_wave2_stale_extract.csv`, a small stale roster extract with partner-contact IDs, company variations, tier labels, segment labels, and category labels.

Solver-visible inputs are `input/prompt.txt`, `input/payloads/answer_template.json`, and the stale roster CSV. The prompt intentionally does not list the operating procedure. It names the roster and asks for structured JSON using `<TASK_ENV_BASE_URL>`. The required output includes `roster_id`, `batch_id`, `qualified_partner_contact_count`, `blocked_or_suppressed_ids`, `needs_manual_review_ids`, `canonical_partner_contacts`, `segment_counts`, `category_counts`, `partner_tier_counts`, `duplicate_person_keys`, `decision_audit`, `source_lineage_audit`, `category_alias_audit`, `review_reason_counts`, and `quality_flags`.

The authoritative CRM slice for `partner_onboarding_wave2` has twelve source contact rows and eight canonical people after rework. `P_POW_001` has a verified CRM contact and duplicate event/roster rows; the canonical analytics-ready contact is `CR_POW_017`, paired with roster source `PC_POW_001`. `P_POW_003` and `P_POW_008` have no reachable email or phone and require manual review. `P_POW_004` has a stale do-not-contact source row `CR_POW_020` and a later steward-corrected active row `CR_POW_024`; `PC_POW_003` is blocked/suppressed as a source row, while `PC_POW_004` is the qualified canonical partner row. `P_POW_005` and `P_POW_009` are suppressed or revoked. `P_POW_006` qualifies through `CR_POW_022`. `P_POW_007` adds the new Nimbus Freight company with one current qualified CRM row, one stale inactive CRM row, and duplicate roster/category evidence.

The standard answer has four qualified partner contacts: `P_POW_001`, `P_POW_004`, `P_POW_006`, and `P_POW_007`. The blocked or suppressed roster source IDs are `PC_POW_003`, `PC_POW_005`, and `PC_POW_010`. Manual-review IDs are `PC_POW_002`, `PC_POW_007`, `PC_POW_009`, `PC_POW_011`, and `PC_POW_012`. Duplicate person keys are `P_POW_001`, `P_POW_004`, and `P_POW_007`. Segment/category/tier counts are for qualified contacts only: `partner = 3`, `ops_lead = 1`; `freight = 2`, `accessorial = 1`, `maintenance = 1`; `platinum = 1`, `gold = 2`, `bronze = 1`.

The task fits the group because it combines CRM/contact reconciliation with category normalization, both recurring operation families in the design. The local extract provides partner-specific exploration: tier labels, company-name variation, and stale references to CRM rows. The environment provides the authoritative contact state and category alias table. The correct solution depends on reconciling those sources rather than trusting a single local file.

Evaluation uses ten exact-match scoring points with raw weights totaling 16:

1. `SP001_target_and_qualified_count`, weight 3: roster ID, batch ID, and qualified count.
2. `SP002_blocked_or_suppressed_ids`, weight 1: blocked/suppressed source roster IDs.
3. `SP003_manual_review_ids`, weight 3: manual-review source roster IDs and lineage evidence.
4. `SP004_qualified_canonical_partner_contacts`, weight 1: canonical rows for `P_POW_001`, `P_POW_004`, `P_POW_006`, and `P_POW_007` plus lineage evidence.
5. `SP005_nonqualified_canonical_partner_contacts`, weight 1: canonical rows for `P_POW_003`, `P_POW_005`, `P_POW_008`, and `P_POW_009`.
6. `SP006_segment_category_and_tier_counts`, weight 1: normalized counts for qualified contacts only plus category alias audit rows.
7. `SP007_duplicate_person_keys`, weight 1: duplicate person keys.
8. `SP008_review_reasons_and_quality_flags`, weight 1: review reason counts and audit flags.
9. `SP009_source_lineage_audit`, weight 3: person-level roster and CRM lineage audit rows.
10. `SP010_category_alias_audit`, weight 1: row-level category alias audit evidence.

Transfer anchors are `train_001`, `train_004`, and `train_005`. From `train_001`, solvers should transfer CRM canonicalization, email/phone normalization, duplicate-person grouping, and suppression handling. From `train_004`, they should transfer reachable-qualified counting, blocked versus manual-review separation, and domain/contactability style reasoning, although this task uses partner roster rows rather than campaign members. From `train_005`, they should transfer controlled category alias mapping and ambiguous-alias review behavior. Task-specific difficulty comes from partner tiers, company-name variation, and deciding how to use the stale partner extract alongside the live CRM rows.

Likely model pitfalls include counting roster source rows instead of unique qualified people, hard-blocking all of `P_POW_004` because one stale source row is do-not-contact, retaining `P_POW_005` or `P_POW_009` despite suppression or revoked consent, counting manual-review or blocked rows in the segment/category/tier counts, using stale CRM rows such as `CR_POW_018` or `CR_POW_028` instead of the selected canonical rows, missing the ambiguous `misc partner services` category rows, and treating company-name punctuation variants as separate partner companies.

Construction record: created by task-builder subagent for `test_004` on 2026-07-07. Files created under `task_group/task_group_021/test_tasks/004/` only. The evaluator is deterministic and scores `output/answer.json` as full credit.

## 中文

本任务属于 `task_group_021`，场景为 `SCN_021_data_cleaning_quality_pipeline`，来源样例为 `E001`、`E002` 和 `E003`。它实现 `test_004` 的测试任务设计：清洗 `partner_onboarding_wave2` 合作伙伴入驻名单，并判断哪些联系人可以进入合作伙伴分析表。共享环境数据来自 `env/data/asterops_data.json`，重点使用 `crm_contact_rows`、`reference_category_aliases` 和 `reference_quality_rules`。任务本地材料是 `input/payloads/partner_onboarding_wave2_stale_extract.csv`，其中包含合作伙伴联系人 ID、公司名称变体、层级标签、分段标签和类别标签，是一个小型过期名单导出。

求解者可见输入为 `input/prompt.txt`、`input/payloads/answer_template.json` 和过期名单 CSV。提示词有意不列出完整操作流程，只说明目标名单，并要求使用 `<TASK_ENV_BASE_URL>` 返回结构化 JSON。输出必须包含 `roster_id`、`batch_id`、`qualified_partner_contact_count`、`blocked_or_suppressed_ids`、`needs_manual_review_ids`、`canonical_partner_contacts`、`segment_counts`、`category_counts`、`partner_tier_counts`、`duplicate_person_keys`、`decision_audit`、`source_lineage_audit`、`category_alias_audit`、`review_reason_counts` 和 `quality_flags`。

返工后的 `partner_onboarding_wave2` 权威 CRM 切片有 12 条联系人来源行和 8 个规范化人员。`P_POW_001` 有已验证 CRM 联系人以及重复的 event/roster 行，最终可入表联系人为 `CR_POW_017`，对应名单来源 `PC_POW_001`。`P_POW_003` 和 `P_POW_008` 缺少可联系邮箱或电话，因此需要人工复核。`P_POW_004` 同时有过期的 do-not-contact 来源行 `CR_POW_020` 和较新的 steward 修正 active 行 `CR_POW_024`；`PC_POW_003` 作为来源行被阻断/抑制，而 `PC_POW_004` 是合格的规范合作伙伴行。`P_POW_005` 和 `P_POW_009` 被抑制或 revoked。`P_POW_006` 通过 `CR_POW_022` 合格。`P_POW_007` 是新增 Nimbus Freight 公司，包含一个当前合格 CRM 行、一个过期 inactive CRM 行，以及重复 roster/category 证据。

标准答案有 4 个合格合作伙伴联系人：`P_POW_001`、`P_POW_004`、`P_POW_006` 和 `P_POW_007`。被阻断或抑制的名单来源 ID 是 `PC_POW_003`、`PC_POW_005` 和 `PC_POW_010`。需要人工复核的 ID 是 `PC_POW_002`、`PC_POW_007`、`PC_POW_009`、`PC_POW_011` 和 `PC_POW_012`。重复人员键为 `P_POW_001`、`P_POW_004` 和 `P_POW_007`。分段、类别和层级计数只统计合格联系人：`partner = 3`、`ops_lead = 1`；`freight = 2`、`accessorial = 1`、`maintenance = 1`；`platinum = 1`、`gold = 2`、`bronze = 1`。

本任务符合任务组设计，因为它结合了 CRM/联系人对账和类别规范化这两个反复出现的操作族。本地导出提供了合作伙伴特有的探索点：层级标签、公司名称变体以及指向 CRM 行的过期引用。共享环境提供权威联系人状态和类别别名表。正确解法需要综合这些来源，而不是只相信某一个本地文件。

评估器使用 10 个精确匹配评分点，原始权重总和为 16：

1. `SP001_target_and_qualified_count`，权重 3：名单 ID、批次 ID 和合格数量。
2. `SP002_blocked_or_suppressed_ids`，权重 1：被阻断/抑制的来源名单 ID。
3. `SP003_manual_review_ids`，权重 3：需要人工复核的来源名单 ID 和 lineage 证据。
4. `SP004_qualified_canonical_partner_contacts`，权重 1：`P_POW_001`、`P_POW_004`、`P_POW_006`、`P_POW_007` 的规范化联系人行和 lineage 证据。
5. `SP005_nonqualified_canonical_partner_contacts`，权重 1：`P_POW_003`、`P_POW_005`、`P_POW_008` 和 `P_POW_009` 的规范化非合格联系人行。
6. `SP006_segment_category_and_tier_counts`，权重 1：仅针对合格联系人的规范分段、类别、层级计数，以及 category alias 审计行。
7. `SP007_duplicate_person_keys`，权重 1：重复人员键。
8. `SP008_review_reasons_and_quality_flags`，权重 1：复核原因计数和审计质量标记。
9. `SP009_source_lineage_audit`，权重 3：人员级 roster 和 CRM lineage 审计行。
10. `SP010_category_alias_audit`，权重 1：行级 category alias 审计证据。

迁移锚点是 `train_001`、`train_004` 和 `train_005`。从 `train_001` 可迁移 CRM 规范化、邮箱/电话标准化、重复人员分组和抑制处理。从 `train_004` 可迁移可联系且合格的计数方式、阻断与人工复核的区分，以及联系人可触达性的判断习惯，虽然本任务使用的是 partner roster 行而不是 campaign member 行。从 `train_005` 可迁移受控类别别名映射和模糊别名进入复核的处理方式。任务特有难点来自合作伙伴层级、公司名称变体，以及如何把过期 partner extract 与实时 CRM 行结合使用。

常见模型错误包括：把名单来源行数当作唯一合格人数；因为 `P_POW_004` 有一条过期 do-not-contact 来源行而错误阻断整个人；在 suppressed 或 revoked 情况下保留 `P_POW_005` 或 `P_POW_009`；把人工复核或阻断行计入分段/类别/层级统计；对 `P_POW_001` 或 `P_POW_007` 使用过期 CRM 行；漏掉 `misc partner services` 的模糊类别行；以及把带标点的公司名称变体当作不同合作伙伴公司。

构建记录：由 `test_004` task-builder subagent 于 2026-07-07 创建。只在 `task_group/task_group_021/test_tasks/004/` 下新增文件。评估器为确定性评估，并且会将 `output/answer.json` 评为满分。
## Rework addendum / 返工补充

English: The final evaluator binds partner qualification, suppression, manual-review, canonical-contact, and quality-flag scoring to `decision_audit` business evidence: source-precedence overrides, suppressed source rows, and channel-normalization changes. A later calibration rework expanded the roster to 12 source rows and added `source_lineage_audit` plus `category_alias_audit` so scoring depends on recoverable row-level reconciliation evidence rather than small aggregate lists. The transfer anchors are `train_001`, `train_004`, and category experience from `train_005`.

中文：最终评测器将伙伴准入、抑制、人工复核、规范联系人和质量标志评分绑定到 `decision_audit` 业务证据：来源优先级覆盖、被抑制的来源行和渠道规范化变化。后续校准返工把 roster 扩展到 12 条来源行，并加入 `source_lineage_audit` 和 `category_alias_audit`，使评分依赖可恢复的行级对账证据，而不是小规模聚合列表。迁移锚点是 `train_001`、`train_004`，以及来自 `train_005` 的类别经验。
