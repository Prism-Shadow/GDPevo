# Test 003 Notes / 测试 003 说明

## English

Task purpose: this test task asks for a structured sourcing shortlist and nomination-gate packet for `PRG-NOVA-31`, focused on `SEN-NOVA` and RFQ packet `NOVA-SRC-31`. It converts the E003 sourcing workflow theme into operational ERP evidence: candidate shortlist decisions, supplier risk checks, commercial support, and a controlled nomination-gate result.

Data sources: the solver-visible prompt points to the shared ProcureOps API and the small English-only local memo `input/payloads/sourcing_memo.md`. The memo contains only RFQ response cards and a signoff tracker. Authoritative operational records come from the API endpoints for programs, suppliers, contracts, purchase requisitions, purchase orders, receipts, AP invoices, AP payments, budget snapshots, and vendor risk events.

Gold derivation: `REQ-NOVA-302` requests 180 units of `SEN-NOVA` by 2026-06-22. `PRG-NOVA-31` is owned by Ravi Menon and has budget headroom of `420000.00 - 358204.15 = 61795.85`. `SUP-HEXEL` is the preferred shortlisted supplier because it is active, has active commercial basis `CR-NOVA-311`, PO `PO-NOVA-3107`, receipt `RCV-GOLD-27`, approved invoice `AP-HEXEL-3309`, and scheduled payment `PAY-00001`; it remains at risk because open or monitoring supplier events `VRE-00010` and `VRE-00032` exist as of 2026-06-01. `SUP-ORION` is a backup shortlist supplier because it is active, low risk, technically approved, and has enough memo capacity but lacks a signed Nova commercial basis. `SUP-BLUESTEM` is excluded for conditional technical fit, capacity shortfall, missing contract, and supplier risk events `VRE-00001` and `VRE-00017`. `SUP-NORD` is excluded because the API supplier status is `quality_hold` and risk rating is `high`.

Nomination gate basis: the memo's signoff tracker shows ER, Finance, and Quality signed, while Program Manager is pending. The selected supplier is therefore not cleared for final nomination; the expected gate decision is `hold_for_missing_program_manager_signoff`, readiness `at_risk`, next owner `program_owner`, and committee routing `no`.

Train anchors: `train_tasks/001` anchors the nomination-readiness structure, as-of supplier risk handling, shortlist/hold style decisions, and budget-headroom convention. `train_tasks/002` anchors supplier risk and blocker-code reconciliation against operational records. `train_tasks/003` anchors use of invoice, receipt, and payment evidence to support release-style business decisions.

Evaluation: seven exact-match scoring points use raw weights `1, 2, 2, 2, 2, 2, 1`. Lists are normalized as sets, candidate rows are matched by `supplier_id`, and USD fields are rounded to cents. The scoring points cover scope and requirement; program budget and shortlist sets; candidate API status and risk; sourcing decisions and blockers; selected supplier commercial support; nomination gate signoffs and decision; and recommended actions/source records.

Construction record: the requested `scratch/task_group_design.md` was not present under this task factory's scratch directory at build time. The available workspace-level `scratch/task_builder_context.md`, the seed E003 sourcing-rubric anchors, existing train tasks, and the shared environment data were used. Files were created only under `task_group/task_group_006/test_tasks/003/`.

## 中文

任务目的：本测试任务要求为 `PRG-NOVA-31` 生成结构化的供应商 shortlist 与 nomination gate 数据包，核心对象是 `SEN-NOVA` 和 RFQ 包 `NOVA-SRC-31`。它把 E003 中的采购寻源流程主题转化为运营证据：候选供应商筛选、供应商风险核查、商业依据以及受控的提名关口结论。

数据来源：求解器可见的 prompt 指向共享 ProcureOps API 和一个英文小备忘录 `input/payloads/sourcing_memo.md`。备忘录只包含 RFQ 响应卡和签批跟踪表。权威运营记录来自 API 中的 programs、suppliers、contracts、purchase requisitions、purchase orders、receipts、AP invoices、AP payments、budget snapshots 和 vendor risk events 等端点。

标准答案推导：`REQ-NOVA-302` 要求在 2026-06-22 前采购 180 件 `SEN-NOVA`。`PRG-NOVA-31` 的负责人是 Ravi Menon，预算余量为 `420000.00 - 358204.15 = 61795.85`。`SUP-HEXEL` 是首选 shortlist 供应商，因为它状态为 active，具备有效商业依据 `CR-NOVA-311`、采购订单 `PO-NOVA-3107`、收货 `RCV-GOLD-27`、已批准发票 `AP-HEXEL-3309` 和计划付款 `PAY-00001`；但截至 2026-06-01 仍存在 open 或 monitoring 风险事件 `VRE-00010` 与 `VRE-00032`，所以仍有风险。`SUP-ORION` 是备选 shortlist 供应商，因为其状态 active、风险低、技术通过且备忘录中的产能足够，但缺少签署后的 Nova 商业依据。`SUP-BLUESTEM` 因技术条件通过、产能不足、缺少合同且存在 `VRE-00001` 与 `VRE-00017` 风险事件而被排除。`SUP-NORD` 因 API 中供应商状态为 `quality_hold` 且风险等级为 `high` 而被排除。

提名关口依据：备忘录中的签批跟踪表显示 ER、Finance、Quality 已签批，而 Program Manager 仍为 pending。因此所选供应商尚未满足最终提名条件；期望关口决策是 `hold_for_missing_program_manager_signoff`，readiness 为 `at_risk`，下一责任人为 `program_owner`，不提交委员会。

训练锚点：`train_tasks/001` 锚定 nomination readiness 结构、按 as-of date 处理供应商风险、shortlist/hold 决策方式和预算余量口径。`train_tasks/002` 锚定供应商风险与 blocker code 对运营记录的核对方式。`train_tasks/003` 锚定使用发票、收货和付款证据支撑业务放行类决策的方法。

评估方式：评估器包含 7 个 exact-match 评分点，原始权重为 `1, 2, 2, 2, 2, 2, 1`。列表按集合归一化，候选供应商行按 `supplier_id` 匹配，美元金额四舍五入到美分。评分点覆盖范围与需求、项目预算和 shortlist 集合、候选供应商 API 状态与风险、寻源决策和阻断项、所选供应商商业证据、提名关口签批与决策、建议动作与来源记录。

构建记录：构建时在本 task factory 的 scratch 目录下未发现所要求的 `scratch/task_group_design.md`。本任务依据可用的 workspace-level `scratch/task_builder_context.md`、种子 E003 寻源 rubric 锚点、已有训练任务和共享环境数据构建。只在 `task_group/task_group_006/test_tasks/003/` 下创建文件。
