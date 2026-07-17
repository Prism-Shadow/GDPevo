# test_004 Notes

## English

Task definition: this formal test task asks the solver to correct a stale WH-BLUE regional receiving dashboard for the North America operating review as of 2026-06-10. The solver sees only an English prompt, a stale dashboard export, and an answer template. The shared ProcureOps API provides the authoritative receipt, PO, AP invoice, and vendor-risk records.

Data lineage: the task belongs to `SCN_006_erp_procurement_supplier_receiving` and uses the generated environment under `task_group/task_group_006/env/`. The target slice is the local export's five WH-BLUE receipt IDs: `RCV-BLUE-14`, `RCV-00001`, `RCV-00004`, `RCV-00007`, and `RCV-00020`.

Solution basis: `RCV-BLUE-14` and `RCV-00001` are separate receipt rows for `PO-AX17-4481`; each must be matched to its invoice-linked AP record rather than merged by PO. `AP-LUMA-7714` is on `QTY_VARIANCE` hold with 24 billed-over-received units worth 2,028.00 USD. `AP-00001` is on `PRICE_VARIANCE` hold with 83 billed-over-received units worth 7,013.50 USD. `RCV-00004` has current approved AP invoice `AP-00007`, so it is the only release candidate, but it carries supplier-risk context through `VRE-00007`. `RCV-00007` has only a future invoice dated after the review date, so it remains not invoiced as of 2026-06-10 and its unbilled receipt value is 7,366.97 USD. `RCV-00020` is tied to held invoice `AP-00032` with `NO_RECEIPT` code and a 4-unit AP variance worth 1,183.76 USD. Open supplier-risk events are `VRE-00005`, `VRE-00007`, `VRE-00009`, and `VRE-00017`.

Scoring points: the evaluator has ten exact-match scoring points with raw weights `[3, 3, 2, 2, 3, 2, 2, 1, 3, 3]`: scope and target receipt set; dashboard row identities and operational statuses; AP hold/release/not-invoiced control sets; corrected row statuses and owners; quantity variances and financial totals; supplier-risk overlay; source precedence and stale export corrections; follow-up actions; transfer source-precedence and AP release policies; and chargeback, payment, and no-receipt transfer policies.

Train anchors: `train_002` anchors receipt, PO, AP invoice, and supplier-risk joins plus the distinction between receipt acceptance and AP release. `train_003` anchors AP close conventions, controlled hold codes, and invoice-to-receipt matching. `train_005` anchors invoice-linked receipt selection, same-PO receipt exclusion, net release versus hold decisions, and precedence of authoritative system/register data over request notes. This test changes the shape into a regional dashboard correction with a stale export and as-of filtering.

Construction record: created by the `test_004` task-builder subagent on 2026-06-01. Only files under `task_group/task_group_006/test_tasks/004/` were created or edited. The task-specific `scratch/task_group_design.md` file was not present in this workspace, so the task follows the available shared builder context, the explicit user brief, and the existing train-task transfer anchors.

Final calibration note: the last scoring point separately checks completeness of the chargeback, payment, and no-receipt transfer policies. It is supported by train-task AP release, chargeback, and source-precedence rules.

## 中文

任务定义：这是一个正式测试任务，要求求解者为 2026-06-10 的北美运营复盘修正 WH-BLUE 区域收货看板。求解者只能看到英文 prompt、一个过期的看板导出文件和答案模板。共享 ProcureOps API 提供权威的收货、采购订单、应付发票和供应商风险记录。

数据来源：本任务属于 `SCN_006_erp_procurement_supplier_receiving`，使用 `task_group/task_group_006/env/` 下的生成环境。目标范围来自本地导出文件中的五个 WH-BLUE 收货 ID：`RCV-BLUE-14`、`RCV-00001`、`RCV-00004`、`RCV-00007` 和 `RCV-00020`。

答案依据：`RCV-BLUE-14` 和 `RCV-00001` 都属于 `PO-AX17-4481`，但必须分别匹配到各自发票记录，不能只按 PO 合并。`AP-LUMA-7714` 处于 `QTY_VARIANCE` hold，已开票未收货差异为 24 件、金额 2,028.00 美元；`AP-00001` 处于 `PRICE_VARIANCE` hold，差异为 83 件、金额 7,013.50 美元。`RCV-00004` 有截至复盘日有效的已批准发票 `AP-00007`，因此是唯一 release candidate，但仍需要携带 `VRE-00007` 的供应商风险背景。`RCV-00007` 只有复盘日之后的未来发票，因此截至 2026-06-10 仍为未开票，未开票收货价值为 7,366.97 美元。`RCV-00020` 对应处于 hold 的 `AP-00032`，hold code 为 `NO_RECEIPT`，AP 数量差异为 4 件、金额 1,183.76 美元。开放供应商风险事件为 `VRE-00005`、`VRE-00007`、`VRE-00009` 和 `VRE-00017`。

评分点：评估器包含 8 个精确匹配评分点，原始权重为 `[3, 3, 2, 2, 3, 2, 2, 1]`，分别检查范围与目标收货集合、看板行身份和业务状态、AP hold/release/未开票集合、修正后的行状态和责任方、数量差异和金额汇总、供应商风险覆盖、来源优先级与过期导出修正、以及后续动作集合。

训练锚点：`train_002` 锚定收货、采购订单、AP 发票和供应商风险的关联方式，以及“收货已接受”和“AP 可释放”之间的区别。`train_003` 锚定 AP 结账、受控 hold code、发票到收货记录匹配等规则。`train_005` 锚定按发票关联的收货选择、同 PO 但不同发票收货的排除、净额释放与 hold 判断，以及权威系统数据优先于请求备注的来源优先级。本测试把这些规则转换成区域看板修正、过期导出和 as-of 日期过滤场景。

构建记录：由 `test_004` task-builder subagent 于 2026-06-01 创建。只创建或编辑了 `task_group/task_group_006/test_tasks/004/` 下的文件。当前工作区没有任务专用的 `scratch/task_group_design.md`，因此本任务依据可用的共享 builder context、用户明确 brief 和已有训练任务迁移锚点完成。
