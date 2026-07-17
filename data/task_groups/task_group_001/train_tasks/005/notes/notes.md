# train_005 Hidden Notes

## English

This task belongs to `task_group_001`, source scenario `SCN_001_crm_marketing_lead_capture`, using source examples `E001`, `E002`, and `E003` as design lineage. The concrete task brief is the train prospecting-plus-CRM-enrichment task: prioritize robotics exhibitors from `AquaFarm Robotics Forum 2026` (`show_id` `aquafarm_robotics_2026`) and identify existing CRM overlaps.

The visible inputs are `input/prompt.txt`, `input/payloads/answer_template.json`, and the shared HarborCRM API under `task_group_001/env/`. The relevant environment data is in `env/data/harborcrm_data.json` and is publicly reachable through `/api/tradeshows/aquafarm_robotics_2026/exhibitors`, `/api/tradeshows/aquafarm_robotics_2026/meeting_interest`, `/api/crm/accounts`, `/api/crm/contacts`, and `/api/policies`. No task-local answer data is exposed to solvers.

The task fits the group because it exercises the same front-of-funnel CRM workflow as the source trade-show prospecting example: turn a noisy exhibitor directory and CRM overlap evidence into an import-ready account plan. It also reinforces the group transfer rules for manufacturer/OEM qualification, distributor/service exclusion, controlled platform labels, existing-account update decisions, and structured CRM action enums.

Material map: `prompt.txt` states the business request, target show ID, API surfaces, ranking rule, and opportunity sizing rule. `answer_template.json` defines the required JSON shape, enum values, ordering rules, and integer USD precision. `output/answer.json` is the standard answer. `eval/eval.sh` delegates to `eval/evaluator.py`, which exact-checks six scoring points and prints a JSON score report.

Solution basis: AquaFarm has five exhibitors. Three qualify because they are manufacturers or OEMs: `ReefWorks Robotics`, `Pelagic Droneworks`, and `ClearPen Optics`. `ReefWorks Robotics` is already present in CRM as `acct_reefworks`, so its action is `update_existing`; the other two qualified exhibitors have no CRM account ID and use `create_account`. Two exhibitors are excluded: `FarmGate Analytics` is a service provider and `SouthPier Robotics Supply` is a distributor. Meeting-interest records rank the qualified leads as ReefWorks first (`requested_demo=true`, score 93), Pelagic second (`requested_demo=true`, score 88), and ClearPen third (`requested_demo=false`, score 64). Priority tiers and opportunity estimates are A/USD 120000, B/USD 90000, and C/USD 50000 respectively, for a total of USD 260000. Platform coverage counts are AUV 1, ROV 1, and Underwater Camera 2.

Evaluation basis: six scoring points are used. SP001 weight 3 checks the ranked qualified robotics lead order. SP002 weight 2 checks per-lead platform coverage and aggregate platform counts. SP003 weight 2 checks CRM action and account ID per ranked lead. SP004 weight 2 checks the excluded non-manufacturer accounts and reasons. SP005 weight 2 checks priority tiers, per-lead opportunity estimates, and total estimated opportunity. SP006 weight 1 checks qualified count, CRM overlap count, and overlap account IDs. All checks are exact after simple structural normalization; there is no free-text scoring.

Transfer design: solving this train task should teach that prospecting qualification depends on relationship type and platform manufacturing authority, not on keyword mentions alone. It should also teach that CRM overlaps should normally become updates rather than account creates, and that near-miss robotics-related companies must still be carried in an explicit exclusion list with controlled reasons. These habits anchor the later test prospecting tasks without exposing their answers.

Construction record: authored by Codex task-builder for `train_005` on 2026-06-01. Created the prompt, answer template, hidden notes, standard answer, evaluator helper, and eval entry point. The environment data itself was not modified.

## 中文

本任务属于 `task_group_001`，来源场景为 `SCN_001_crm_marketing_lead_capture`，设计脉络来自源示例 `E001`、`E002`、`E003`。具体任务是训练集中的“展会获客加 CRM 补全”任务：从 `AquaFarm Robotics Forum 2026`（`show_id` 为 `aquafarm_robotics_2026`）中优先筛选机器人相关参展商，并识别已有 CRM 重叠账号。

求解者可见输入包括 `input/prompt.txt`、`input/payloads/answer_template.json`，以及 `task_group_001/env/` 下的 HarborCRM 共享 API。相关环境数据位于 `env/data/harborcrm_data.json`，并可通过 `/api/tradeshows/aquafarm_robotics_2026/exhibitors`、`/api/tradeshows/aquafarm_robotics_2026/meeting_interest`、`/api/crm/accounts`、`/api/crm/contacts` 和 `/api/policies` 访问。任务没有向求解者暴露本地答案端点。

该任务符合任务组主题，因为它复用了源示例中的前端 CRM 工作流：把带噪声的展商目录和 CRM 重叠证据转化为可导入的客户计划。它也强化了任务组中的迁移规则，包括制造商/OEM 资格判断、排除经销商和服务商、使用受控平台标签、已有账号更新动作，以及结构化 CRM 动作枚举。

材料地图：`prompt.txt` 给出业务请求、目标展会 ID、API 范围、排序规则和商机金额规则。`answer_template.json` 定义 JSON 结构、枚举值、排序规则和 USD 整数精度。`output/answer.json` 是标准答案。`eval/eval.sh` 调用 `eval/evaluator.py`，精确检查六个评分点并输出 JSON 评分报告。

答案依据：AquaFarm 一共有五个参展商。其中三个合格，因为它们是制造商或 OEM：`ReefWorks Robotics`、`Pelagic Droneworks`、`ClearPen Optics`。`ReefWorks Robotics` 已在 CRM 中存在，对应 `acct_reefworks`，所以动作为 `update_existing`；另外两个合格展商没有 CRM 账号 ID，动作为 `create_account`。两个展商被排除：`FarmGate Analytics` 是服务商，`SouthPier Robotics Supply` 是经销商。会议意向数据使合格线索排序为 ReefWorks 第一（请求演示，93 分）、Pelagic 第二（请求演示，88 分）、ClearPen 第三（未请求演示，64 分）。优先级和商机估值分别是 A/USD 120000、B/USD 90000、C/USD 50000，总计 USD 260000。平台覆盖计数为 AUV 1、ROV 1、Underwater Camera 2。

评估依据：本任务使用六个评分点。SP001 权重 3，检查合格机器人线索排序。SP002 权重 2，检查每个线索的平台覆盖和聚合平台计数。SP003 权重 2，检查每个排序线索的 CRM 动作和账号 ID。SP004 权重 2，检查被排除的非制造商账号及原因。SP005 权重 2，检查优先级、每条线索的商机估值和总估值。SP006 权重 1，检查合格数量、CRM 重叠数量和重叠账号 ID。所有检查均为简单结构归一化后的精确匹配，不评估自由文本质量。

迁移设计：完成该训练任务后，模型应学会展会获客资格取决于关系类型和平台制造权限，而不是只看关键词。它还应学会 CRM 重叠通常意味着更新已有账号而不是新建账号，并且机器人相关但不合格的近似对象也需要以受控原因进入排除列表。这些经验会支撑后续测试集获客任务，但不会直接暴露测试答案。

构造记录：由 Codex `train_005` task-builder 于 2026-06-01 创建。新增了 prompt、答案模板、隐藏 notes、标准答案、评估辅助脚本和 eval 入口。共享环境数据未被修改。
