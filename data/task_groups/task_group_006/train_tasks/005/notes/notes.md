# train_005 Notes

## English

This task belongs to `SCN_006_erp_procurement_supplier_receiving` in `task_group_006`. It uses the shared ProcureOps API plus the task-local `input/payloads/ap_release_packet.json` to ask for a mixed receiving and AP chargeback release file for AX17 records. The current workspace did not contain `scratch/task_group_design.md`; the available shared context and environment anchors were used, and the task follows the requested brief for AX17 plus generated PO-style records.

The solver sees only an English prompt, the answer template, and a small release packet. The packet names the target IDs: `PRG-AX17`, POs `PO-AX17-4481`, `PO-AX17-4519`, `PO-00031`, and `PO-00038`; receipts `RCV-BLUE-14`, `RCV-00017`, and `RCV-00020`; and AP invoices `AP-LUMA-7714`, `AP-VANTIX-2188`, `AP-00027`, and `AP-00032`. Exact PO-73xx IDs are absent from the shared data, so `PO-00031` and `PO-00038` are used as the available generated PO records and are explicitly named in the payload.

The expected work is to query the shared API for purchase orders, receipts, and AP invoices, then combine that state with the local chargeback register excerpt. The release note and PO-73xx alias note are supporting context only. The authoritative sources are ProcureOps PO, receipt, and AP records plus the local chargeback register excerpt because the shared environment does not expose a chargeback endpoint.

Solution basis: `AP-LUMA-7714` is tied to `RCV-BLUE-14`, where 216 units were received against a 240-unit AP bill, producing an approved underage chargeback of `24 * 84.50 = 2028.00`; the later same-PO receipt `RCV-00001` belongs outside this invoice release line. `AP-00032` has accepted receipt `RCV-00020`, but the invoice bills four more units than the accepted receipt, producing an approved AP quantity variance of `4 * 295.94 = 1183.76`. `AP-VANTIX-2188` remains held because `PO-AX17-4519` has no receipt. `AP-00027` is not released because `RCV-00017` is still in inspection hold with a pending underage chargeback of `99 * 84.50 = 8365.50`. Approved chargebacks total `3211.76`, pending chargebacks total `8365.50`, and the net AP release total is `48058.94`.

Evaluation uses eight exact-match scoring points with raw weights `[3, 3, 2, 2, 3, 2, 2, 1]`: target IDs and review date; invoice decisions and reasons; receipt inclusion and exclusion; per-invoice financial amounts; release/hold sets and totals; receiving exception classifications; source precedence; and follow-up actions. Lists are normalized by the evaluator, and currency is rounded to cents.

As a train task, this teaches transferable conventions through answer comparison rather than through the prompt: match AP release to the invoice-linked receipt, treat similar same-PO receipts as exclusions when they belong to another invoice, use approved chargebacks for net release, hold pending quality or missing-receipt cases, and separate authoritative system/register sources from supporting request notes.

Construction record: author `task-builder subagent train_005`; created 2026-06-01; updated 2026-06-01. Major changes: created the prompt, AP release packet, answer template, standard answer, exact-match evaluator, and bilingual notes.

## 中文

本任务属于 `SCN_006_erp_procurement_supplier_receiving`，任务组为 `task_group_006`。它使用共享的 ProcureOps API 和任务本地文件 `input/payloads/ap_release_packet.json`，要求为 AX17 相关记录制作收货、应付账款与 chargeback 混合释放文件。当前工作区没有 `scratch/task_group_design.md`，因此本任务依据可用的共享上下文和环境锚点构造，并遵循用户指定的 AX17 与生成式 PO 记录要求。

求解者只能看到英文 prompt、答案模板和一个小型 release packet。该 packet 明确列出目标 ID：`PRG-AX17`，采购订单 `PO-AX17-4481`、`PO-AX17-4519`、`PO-00031`、`PO-00038`，收货记录 `RCV-BLUE-14`、`RCV-00017`、`RCV-00020`，以及 AP 发票 `AP-LUMA-7714`、`AP-VANTIX-2188`、`AP-00027`、`AP-00032`。共享数据中不存在精确的 PO-73xx 编号，因此使用可用的生成式共享 ID `PO-00031` 和 `PO-00038`，并在 payload 中明确说明。

预期工作流程是查询共享 API 的 PO、receipt 和 AP invoice 记录，再与本地 chargeback register 摘要合并判断。release request note 和 PO-73xx alias note 只作为辅助上下文。权威来源是 ProcureOps 的 PO、receipt、AP 记录以及本地 chargeback register，因为共享环境没有单独提供 chargeback endpoint。

标准答案依据如下：`AP-LUMA-7714` 关联 `RCV-BLUE-14`，收货 216 件而 AP 计费 240 件，因此批准的 underage chargeback 为 `24 * 84.50 = 2028.00`；同一 PO 的后续收货 `RCV-00001` 不属于该发票释放行，应作为排除项。`AP-00032` 有已接受收货 `RCV-00020`，但发票比已接受收货多计 4 件，因此批准的 AP 数量差异为 `4 * 295.94 = 1183.76`。`AP-VANTIX-2188` 因 `PO-AX17-4519` 没有收货记录而继续 hold。`AP-00027` 因 `RCV-00017` 仍处于 inspection hold，且存在待质量复核的 underage chargeback `99 * 84.50 = 8365.50`，所以不能释放。批准 chargeback 合计 `3211.76`，待定 chargeback 合计 `8365.50`，净释放金额为 `48058.94`。

评估采用 8 个精确匹配评分点，原始权重为 `[3, 3, 2, 2, 3, 2, 2, 1]`：目标 ID 与日期、发票决策和原因、收货纳入与排除、逐发票金额、释放和 hold 集合及总额、收货异常分类、来源优先级、后续动作。评估器会规范化列表顺序，并将货币数值四舍五入到分。

作为训练任务，它通过尝试后对照答案来沉淀可迁移经验，而不是在 prompt 中直接讲 SOP：AP 释放要匹配发票关联的收货；同一 PO 下相似但属于其他发票的收货应排除；批准的 chargeback 可用于净额释放；质量待复核和缺收货记录应继续 hold；系统与 register 记录要区别于请求备注等辅助信息。

构造记录：作者为 `task-builder subagent train_005`；创建日期 2026-06-01；更新日期 2026-06-01。主要变更：创建 prompt、AP release packet、答案模板、标准答案、精确匹配评估器和双语 notes。
