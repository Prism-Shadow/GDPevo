# test_005 Hidden Notes

## English

This task belongs to `task_group_001`, source scenario `SCN_001_crm_marketing_lead_capture`, with design lineage from source examples `E001`, `E002`, and `E003`. The concrete test brief is the prospecting-plus-event-import task from the group design: convert `BlueTech Demo Day 2027` (`show_id` `bluetech_demo_2027`) exhibitor and meeting-interest data into a CRM-ready target account plan.

The visible inputs are `input/prompt.txt`, `input/payloads/answer_template.json`, and the shared HarborCRM API under `task_group_001/env/`. The relevant generated data is in `env/data/harborcrm_data.json` and is publicly reachable through `/api/tradeshows`, `/api/tradeshows/bluetech_demo_2027/exhibitors`, `/api/tradeshows/bluetech_demo_2027/meeting_interest`, `/api/crm/accounts`, `/api/crm/contacts`, and `/api/policies`. No task-local answer endpoint or hidden answer payload is exposed to solvers.

The business task is to prepare a structured target-account plan for field sales after a marine technology demo day. The output must identify qualified platform makers, rank them by meeting-interest signals, assign controlled platform and product-fit enums, decide CRM import action, retain non-qualified exhibitors in an exclusion list, and summarize meeting, overlap, action, platform, and pipeline totals.

Scenario fit: this is a front-of-funnel CRM operation that turns trade-show activity into import-ready account planning. It combines the trade-show prospecting family from `train_002` with the CRM enrichment and ranking habit from `train_005`. The object relationships are show -> exhibitor directory -> meeting-interest records -> CRM accounts/contacts -> account import action.

Material map: `prompt.txt` gives the target show ID, the public API surfaces, and the required target-account planning output. `answer_template.json` defines the solver-visible schema, allowed enums, stable list ordering, and integer USD precision. `output/answer.json` is the standard answer. `eval/eval.sh` is the evaluation contract and delegates to `eval/evaluator.py`. The evaluator exact-checks six scoring points and prints machine-readable JSON.

Solution basis: BlueTech has five exhibitors. Three qualify because they are manufacturers or OEMs of target platforms: `Marlin Autonomous`, `NorthChannel Robotics`, and `TideGlass Imaging`. `Marlin Autonomous` manufactures AUV and ROV platforms and is classified as `auv_rov_manufacturer`. `NorthChannel Robotics` manufactures ROVs with camera platform capability and is classified as `rov_camera_manufacturer`. `TideGlass Imaging` is an OEM underwater camera maker and is classified as `underwater_camera_oem`. All three have meeting-interest records with requested demos. Ranking is Marlin first (score 97), NorthChannel second (score 91), and TideGlass third (score 86). Marlin and NorthChannel are tier A at USD 120000 each; TideGlass is tier B at USD 90000, for total estimated pipeline of USD 330000.

Exclusion basis: `PortSide Marine Sales` is a distributor/dealer and remains excluded even though it requested a demo and mentions ROV/AUV brands. `BlueChem Sensors` is a sensor-only vendor and has no qualifying platform manufacturing role. Excluded exhibitors are sorted by company name. The BlueTech qualified companies have no matching CRM account IDs in the exhibitor records and no matching CRM accounts in the shared CRM account list, so the existing CRM overlap count and update count are both zero; all three target accounts use `create_account`.

Evaluation basis: six scoring points are used. SP001 weight 3 checks the ranked target-account order and key row facts. SP002 weight 3 checks platform coverage, product-fit enums, and platform/product-fit aggregate counts. SP003 weight 2 checks CRM action and account ID per target account, plus create count. SP004 weight 2 checks the excluded reseller and sensor-only accounts, reasons, meeting fields, and no-import action. SP005 weight 3 checks total pipeline, meeting-interest counts, priority tiers, and per-account estimates using the transferable robotics prospecting tier convention from `train_005` (`A` = 120000 USD, `B` = 90000 USD, `C` = 50000 USD). SP006 weight 1 checks existing CRM overlap account IDs, overlap count, and update count. All scoring is exact-match after structural normalization; no free-text explanation is scored.

Transfer design: this test is anchored by `train_002` and `train_005`. From those tasks, a solver should transfer the distinction between manufacturers/OEMs and resellers/service/sensor-only firms, the controlled platform labels `AUV`, `ROV`, and `Underwater Camera`, the habit of keeping excluded near-misses visible with controlled reasons, and the CRM action convention that existing accounts are updates while absent accounts are creates. The task-specific exploration is the BlueTech-specific meeting-interest ordering, product-fit mapping, absence of CRM overlap, and pipeline total. The high-value transfer-dependent goals are SP001 through SP004; SP005 and SP006 require local data exploration and arithmetic.

Construction record: authored by Codex task-builder for `test_005` on 2026-06-01. Created the prompt, answer template, hidden notes, standard answer, evaluator helper, and eval entry point. The shared environment data was not modified.

## 中文

本任务属于 `task_group_001`，来源场景为 `SCN_001_crm_marketing_lead_capture`，设计脉络来自源示例 `E001`、`E002`、`E003`。具体测试任务是任务组设计中的“获客加活动导入”任务：将 `BlueTech Demo Day 2027`（`show_id` 为 `bluetech_demo_2027`）的参展商和会议意向数据转化为可供 CRM 使用的目标账号计划。

求解者可见输入包括 `input/prompt.txt`、`input/payloads/answer_template.json`，以及 `task_group_001/env/` 下的 HarborCRM 共享 API。相关生成数据位于 `env/data/harborcrm_data.json`，并可通过 `/api/tradeshows`、`/api/tradeshows/bluetech_demo_2027/exhibitors`、`/api/tradeshows/bluetech_demo_2027/meeting_interest`、`/api/crm/accounts`、`/api/crm/contacts` 和 `/api/policies` 访问。求解者无法访问按任务暴露的答案端点或隐藏答案负载。

业务任务是在一次海洋技术演示日之后，为外勤销售团队准备结构化目标账号计划。输出需要识别合格的平台制造商，按会议意向信号排序，分配受控的平台和产品适配枚举，决定 CRM 导入动作，将不合格参展商保留在排除列表中，并汇总会议、重叠账号、动作、平台和管道金额。

场景适配：该任务是前端 CRM 运营的一部分，把展会活动转化为可导入的账号计划。它结合了 `train_002` 的展会获客能力和 `train_005` 的 CRM 补全与排序能力。对象关系为展会 -> 参展商目录 -> 会议意向记录 -> CRM 账号/联系人 -> 账号导入动作。

材料地图：`prompt.txt` 给出目标展会 ID、公共 API 范围、排序规则和优先级到管道金额的规则。`answer_template.json` 定义求解者可见的结构、允许枚举、稳定排序规则和 USD 整数精度。`output/answer.json` 是标准答案。`eval/eval.sh` 是评估入口并调用 `eval/evaluator.py`。评估器精确检查六个评分点并输出机器可读 JSON。

答案依据：BlueTech 共有五个参展商。三个合格，因为它们是目标平台的制造商或 OEM：`Marlin Autonomous`、`NorthChannel Robotics`、`TideGlass Imaging`。`Marlin Autonomous` 制造 AUV 和 ROV 平台，产品适配为 `auv_rov_manufacturer`。`NorthChannel Robotics` 制造带摄像平台能力的 ROV，产品适配为 `rov_camera_manufacturer`。`TideGlass Imaging` 是 OEM 水下摄像机制造商，产品适配为 `underwater_camera_oem`。这三家公司都有会议意向记录并请求演示。排序为 Marlin 第一（97 分）、NorthChannel 第二（91 分）、TideGlass 第三（86 分）。Marlin 和 NorthChannel 为 A 级，各 USD 120000；TideGlass 为 B 级，USD 90000；总管道估值为 USD 330000。

排除依据：`PortSide Marine Sales` 是经销商/代理商，即使请求了演示且提到 ROV/AUV 品牌，也应排除。`BlueChem Sensors` 是纯传感器供应商，没有合格的平台制造角色。排除参展商按公司名排序。BlueTech 的合格公司在展商记录中没有 CRM 账号 ID，在共享 CRM 账号列表中也没有匹配账号，所以现有 CRM 重叠数量和更新数量均为零；三个目标账号的动作都是 `create_account`。

评估依据：本任务使用六个评分点。SP001 权重 3，检查目标账号排序和关键行事实。SP002 权重 3，检查平台覆盖、产品适配枚举，以及平台/产品适配聚合计数。SP003 权重 2，检查每个目标账号的 CRM 动作和账号 ID，并检查新建数量。SP004 权重 2，检查被排除的经销商和纯传感器账号、原因、会议字段和 no-import 动作。SP005 权重 3，检查总管道金额、会议意向计数、优先级和单账号估值，并使用从 `train_005` 可迁移的机器人潜客分层估值约定（`A` = 120000 USD，`B` = 90000 USD，`C` = 50000 USD）。SP006 权重 1，检查现有 CRM 重叠账号 ID、重叠数量和更新数量。所有评分都是结构归一化后的精确匹配，不评分自由文本说明。

迁移设计：本测试由 `train_002` 和 `train_005` 锚定。求解者应从这些训练任务迁移制造商/OEM 与经销商/服务商/纯传感器公司的区分，受控平台标签 `AUV`、`ROV`、`Underwater Camera`，将近似但不合格对象保留在排除列表且使用受控原因的习惯，以及已有账号更新、缺失账号新建的 CRM 动作约定。本任务中特有的探索难点是 BlueTech 的会议意向排序、产品适配映射、没有 CRM 重叠这一事实，以及管道金额汇总。高价值的迁移依赖评分点是 SP001 到 SP004；SP005 和 SP006 更依赖本地数据探索和计算。

构造记录：由 Codex `test_005` task-builder 于 2026-06-01 创建。新增了 prompt、答案模板、隐藏 notes、标准答案、评估辅助脚本和 eval 入口。共享环境数据未被修改。
