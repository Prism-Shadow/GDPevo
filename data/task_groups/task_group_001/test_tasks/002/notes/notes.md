# test_002 Hidden Notes

## English

This task belongs to `task_group_001`, sourced from scenario `SCN_001_crm_marketing_lead_capture` and source examples `E001`, `E002`, and `E003`. The specific test brief is the prospecting task for `Nordic Aquaculture Tech 2027` (`show_id` `nordic_aqua_2027`) for LakeHealth integration. The shared generated environment is HarborCRM, with deterministic data in `task_group/task_group_001/env/data/harborcrm_data.json` and construction metadata in `env/data/manifest.json`.

The solver-visible inputs are `input/prompt.txt`, `input/payloads/answer_template.json`, and the public HarborCRM API after `env/setup.sh` is started. Relevant public endpoints include `/api/tradeshows`, `/api/tradeshows/nordic_aqua_2027/exhibitors`, `/api/tradeshows/nordic_aqua_2027/meeting_interest`, `/api/crm/accounts`, and `/api/policies`. The prompt asks for import-ready qualified exhibitors, platform coverage, enrichment fields, near-miss exclusions, and aggregate counts. It intentionally does not expose a procedural SOP or answer path.

The task fits the group because it exercises the same front-of-funnel CRM workflow as the trade-show prospecting source example: convert a noisy exhibitor directory, CRM context, and meeting-interest evidence into a structured account-import list. It uses the task group transfer core around manufacturer/OEM qualification, controlled platform enums, exclusion of non-platform sellers, and import-ready enrichment.

Material map: `prompt.txt` gives the business request, show ID, HarborCRM access hint, and required output location. `answer_template.json` defines the JSON shape, enum choices, ordering rules, and integer count precision. `output/answer.json` is the standard answer. `eval/eval.sh` delegates to `eval/evaluate.py`, which exact-checks six scoring points and emits a JSON score report. Environment data used for answer construction comes from the Nordic exhibitor directory, Nordic meeting-interest records, CRM account overlap fields, and `/api/policies` prospecting enums.

Solution basis: Nordic Aquaculture Tech has five relevant exhibitors. Three qualify because they are manufacturers or OEMs of target platforms: `Nordic Subsea Systems` (`exh_na_001`) manufactures resident ROVs and AUV mapping pods; `LakeHealth Robotics` (`exh_na_002`) builds freshwater AUVs and explicitly welcomes sensor integration partners; `FjordCam OEM` (`exh_na_003`) is an underwater-camera OEM. `AquaSense Nordic` (`exh_na_004`) is excluded as `sensor_vendor_only`, and `Arctic ROV Rentals` (`exh_na_005`) is excluded as `service_only`. Meeting-interest records support priority tiers: LakeHealth Robotics and Nordic Subsea Systems requested demos with high scores and receive tier `A`; FjordCam OEM has a technical-datasheet request without a demo and receives tier `C`.

The standard answer sorts qualified exhibitors by `company_name`: `FjordCam OEM`, `LakeHealth Robotics`, `Nordic Subsea Systems`. Platform coverage is `Underwater Camera`, `AUV`, and `AUV` plus `ROV` respectively. Aggregate counts are qualified total `3`, platform counts `AUV: 2`, `ROV: 1`, `Underwater Camera: 1`, priority counts `A: 2`, `B: 0`, `C: 1`, and excluded near misses total `2`.

Evaluation uses six exact-match scoring points with raw weights `[3, 3, 2, 2, 2, 1]`. SP001 checks the qualified exhibitor set, plus `show_id` and `campaign`. SP002 checks platform labels for each qualified exhibitor. SP003 checks booth, country, and website enrichment. SP004 checks the excluded near-miss set and exclusion-reason enums. SP005 checks priority tiers. SP006 checks aggregate counts. The evaluator normalizes company rows by `company_id`, trims simple text, and permits a trailing slash difference in websites; all business results otherwise require exact structured matches. The standard answer must score `1.0`.

Transfer design: high-value scoring points SP001, SP002, and SP004 are anchored by `train_002` and `train_005`. A solver should transfer the judgment that qualified prospects are manufacturers or OEMs of target platforms, not merely exhibitors that mention ROVs, sensors, rentals, services, or aquaculture. The same train anchors also establish the controlled platform labels and the need to carry near-miss exclusions with enum reasons. SP003, SP005, and SP006 require task-specific exploration of the Nordic data and meeting-interest records. The test remains nontrivial because the show includes multi-platform builders, an existing CRM customer, a campaign-named LakeHealth company, a sensor-only near miss, and a service provider whose description mentions ROVs.

Construction record: authored by Codex task-builder for `test_002` on 2026-06-01. Created the solver prompt, answer template, hidden bilingual notes, standard answer, evaluator helper, and eval entry point. The shared environment data was read but not modified.

Calibration rework on 2026-06-01 added CRM action and pipeline-estimate outputs to reduce direct solvability and strengthen transfer from `train_005`. The added business results are: `FjordCam OEM` should be `create_account` with `50000` USD pipeline under tier `C`; `LakeHealth Robotics` and `Nordic Subsea Systems` should be `update_existing` with existing CRM account IDs and `120000` USD each. The aggregate rollup adds create count `1`, update count `2`, existing CRM overlap count `2`, overlap account IDs, and total estimated pipeline `290000` USD. The task now uses nine scoring points; SP007 checks CRM actions and account IDs, SP008 checks per-lead pipeline estimates, and SP009 checks the CRM overlap and total pipeline rollup. These points are anchored by the `train_005` create/update and robotics tier-valuation convention (`A` = 120000 USD, `B` = 90000 USD, `C` = 50000 USD).

## 中文

本任务属于 `task_group_001`，来源场景为 `SCN_001_crm_marketing_lead_capture`，设计脉络来自源示例 `E001`、`E002` 和 `E003`。具体测试任务是为 `Nordic Aquaculture Tech 2027`（`show_id` 为 `nordic_aqua_2027`）构建 LakeHealth integration 的展会获客名单。共享生成环境是 HarborCRM，确定性数据位于 `task_group/task_group_001/env/data/harborcrm_data.json`，构造元数据位于 `env/data/manifest.json`。

求解者可见输入包括 `input/prompt.txt`、`input/payloads/answer_template.json`，以及启动 `env/setup.sh` 后可访问的 HarborCRM 公共 API。相关公共端点包括 `/api/tradeshows`、`/api/tradeshows/nordic_aqua_2027/exhibitors`、`/api/tradeshows/nordic_aqua_2027/meeting_interest`、`/api/crm/accounts` 和 `/api/policies`。提示要求输出可导入的合格参展商、平台覆盖、补充字段、近似但不合格对象的排除，以及汇总计数。提示刻意不暴露逐步 SOP 或答案路径。

该任务符合任务组主题，因为它复用了源展会获客示例中的前端 CRM 工作流：把有噪声的展商目录、CRM 上下文和会议兴趣证据转化为结构化账号导入名单。它使用任务组的核心迁移能力，包括制造商/OEM 资格判断、受控平台枚举、排除非平台销售方，以及可导入 CRM 的字段补全。

材料地图：`prompt.txt` 给出业务请求、展会 ID、HarborCRM 访问提示和输出要求。`answer_template.json` 定义 JSON 结构、枚举值、排序规则和整数计数精度。`output/answer.json` 是标准答案。`eval/eval.sh` 调用 `eval/evaluate.py`，后者精确检查六个评分点并输出 JSON 评分报告。答案构造使用了 Nordic 展商目录、Nordic 会议兴趣记录、CRM 账号重叠字段，以及 `/api/policies` 中的获客枚举。

答案依据：Nordic Aquaculture Tech 有五个相关参展商。其中三个合格，因为它们是目标平台的制造商或 OEM：`Nordic Subsea Systems`（`exh_na_001`）制造常驻 ROV 和 AUV 测绘模块；`LakeHealth Robotics`（`exh_na_002`）制造淡水 AUV，并明确欢迎传感器集成合作伙伴；`FjordCam OEM`（`exh_na_003`）是水下相机 OEM。`AquaSense Nordic`（`exh_na_004`）作为 `sensor_vendor_only` 排除，`Arctic ROV Rentals`（`exh_na_005`）作为 `service_only` 排除。会议兴趣记录支持优先级：LakeHealth Robotics 和 Nordic Subsea Systems 请求演示且分数较高，优先级为 `A`；FjordCam OEM 请求技术资料但没有演示请求，优先级为 `C`。

标准答案按 `company_name` 对合格参展商排序：`FjordCam OEM`、`LakeHealth Robotics`、`Nordic Subsea Systems`。平台覆盖分别是 `Underwater Camera`、`AUV`、以及 `AUV` 加 `ROV`。汇总计数为合格总数 `3`，平台计数 `AUV: 2`、`ROV: 1`、`Underwater Camera: 1`，优先级计数 `A: 2`、`B: 0`、`C: 1`，近似对象排除总数 `2`。

评估使用六个精确匹配评分点，原始权重为 `[3, 3, 2, 2, 2, 1]`。SP001 检查合格参展商集合，并同时检查 `show_id` 和 `campaign`。SP002 检查每个合格参展商的平台标签。SP003 检查展位、国家和网站补充字段。SP004 检查被排除的近似对象集合和排除原因枚举。SP005 检查优先级。SP006 检查汇总计数。评估器按 `company_id` 归一化公司记录，去除简单文本首尾空格，并允许网站末尾斜杠差异；除此之外，所有业务结果都要求结构化精确匹配。标准答案必须得到 `1.0`。

迁移设计：高价值评分点 SP001、SP002 和 SP004 由 `train_002` 与 `train_005` 锚定。求解者应迁移这样的判断：合格潜客应是目标平台的制造商或 OEM，而不是仅仅提到 ROV、传感器、租赁、服务或水产养殖的参展商。同样的训练锚点还建立了受控平台标签，以及用枚举原因保留近似排除项的要求。SP003、SP005 和 SP006 需要针对 Nordic 数据和会议兴趣记录进行任务内探索。该测试仍然具有难度，因为展会中同时有多平台制造商、已有 CRM 客户、名称与活动相关的 LakeHealth 公司、传感器供应商近似项，以及描述中提到 ROV 的服务商。

构造记录：由 Codex `test_002` task-builder 于 2026-06-01 创建。新增了求解者提示、答案模板、双语隐藏备注、标准答案、评估辅助脚本和 eval 入口。共享环境数据仅被读取，未被修改。

校准返工记录：2026-06-01 增加了 CRM 动作和管道估值输出，以降低直接解题可得分，并加强从 `train_005` 迁移的价值。新增业务结果包括：`FjordCam OEM` 应为 `create_account`，作为 `C` 级管道估值 `50000` USD；`LakeHealth Robotics` 和 `Nordic Subsea Systems` 应为 `update_existing`，包含已有 CRM 账号 ID，且各自估值 `120000` USD。汇总新增新建数 `1`、更新数 `2`、已有 CRM 重叠数 `2`、重叠账号 ID，以及总估值 `290000` USD。任务现在使用九个评分点；SP007 检查 CRM 动作和账号 ID，SP008 检查逐线索管道估值，SP009 检查 CRM 重叠和总管道估值汇总。这些点由 `train_005` 中的新建/更新约定和机器人优先级分层估值约定锚定（`A` = 120000 USD，`B` = 90000 USD，`C` = 50000 USD）。
