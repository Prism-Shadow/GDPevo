export const modes = ["base", "demo", "reflect"];

export const summaryCards = [
  {
    title: "Codex · GPT-5.5",
    thinking: "xhigh",
    rows: [
      { mode: "base", avg: "48.35%", tokens: "709.2", usd: "1.08" },
      { mode: "demo", avg: "65.99%", tokens: "466.1", usd: "0.81" },
      { mode: "reflect", avg: "67.13%", tokens: "458.7", usd: "0.79", best: true }
    ]
  },
  {
    title: "Claude Code · Opus 4.8",
    thinking: "xhigh",
    rows: [
      { mode: "base", avg: "49.11%", tokens: "376.8", usd: "0.61" },
      { mode: "demo", avg: "70.90%", tokens: "340.8", usd: "0.55", best: true },
      { mode: "reflect", avg: "67.94%", tokens: "331.9", usd: "0.56" }
    ]
  },
  {
    title: "Panofy · Opus 4.6",
    thinking: "high",
    rows: [
      { mode: "base", avg: "50.17%", tokens: "318.9", usd: "0.72" },
      { mode: "demo", avg: "68.24%", tokens: "383.5", usd: "0.80", best: true },
      { mode: "reflect", avg: "67.98%", tokens: "365.2", usd: "0.79" }
    ]
  }
];

export const harnesses = [
  { key: "codex", harness: "Codex", model: "GPT-5.5", thinking: "xhigh" },
  { key: "claude", harness: "Claude Code", model: "Opus 4.8", thinking: "xhigh" },
  { key: "panofy", harness: "Panofy", model: "Opus 4.6", thinking: "high" }
];

export const resultGroups = [
  { id: "01", domain: "CRM", en: "Lead capture", zh: "线索捕获", codex: [44.43, 48.12, 57.46], claude: [48.75, 81.96, 75.47], panofy: [63.74, 85.28, 82.26] },
  { id: "02", domain: "CRM", en: "B2B quote", zh: "B2B 报价", codex: [41.62, 51.17, 60.41], claude: [42.74, 58.48, 46.53], panofy: [43.85, 58.93, 51.51] },
  { id: "03", domain: "CRM", en: "Service ticket", zh: "服务工单", codex: [57.84, 78.11, 71.69], claude: [46.69, 70.89, 63.92], panofy: [58.58, 73.41, 58.00] },
  { id: "04", domain: "CRM", en: "Churn analytics", zh: "流失分析", codex: [31.73, 60.94, 59.95], claude: [25.24, 54.55, 54.28], panofy: [18.82, 59.53, 57.06] },
  { id: "05", domain: "ERP", en: "Expense control", zh: "费用控制", codex: [35.09, 52.45, 46.51], claude: [51.15, 57.96, 59.26], panofy: [41.05, 60.51, 62.85] },
  { id: "06", domain: "ERP", en: "Procurement", zh: "采购收货", codex: [66.28, 72.39, 71.76], claude: [67.98, 72.98, 72.54], panofy: [64.83, 72.24, 70.39] },
  { id: "07", domain: "ERP", en: "Inventory", zh: "库存履约", codex: [38.40, 54.31, 54.49], claude: [39.54, 55.76, 57.10], panofy: [36.39, 41.88, 51.15] },
  { id: "08", domain: "Finance", en: "Advisory & tax", zh: "理财税务", codex: [70.57, 93.18, 93.05], claude: [66.89, 93.60, 90.94], panofy: [49.18, 73.36, 79.36] },
  { id: "09", domain: "Finance", en: "Ops modeling", zh: "运营建模", codex: [42.76, 92.47, 80.94], claude: [51.76, 100.00, 80.00], panofy: [62.39, 89.73, 92.47] },
  { id: "10", domain: "Finance", en: "Investment", zh: "投资策略", codex: [60.76, 71.05, 73.77], claude: [58.60, 63.45, 75.07], panofy: [50.73, 65.18, 63.90] },
  { id: "11", domain: "Finance", en: "Credit risk", zh: "信用风险", codex: [45.68, 56.48, 65.41], claude: [41.56, 63.48, 60.82], panofy: [48.91, 56.38, 61.07] },
  { id: "12", domain: "ERP", en: "HR lifecycle", zh: "HR 生命周期", codex: [45.08, 61.24, 70.10], claude: [48.41, 77.66, 79.30], panofy: [63.59, 82.43, 85.77] }
];

export const taskGroups = [
  { id: "001", label: "01", domain: "CRM", en: "Marketing lead capture", zh: "市场营销线索捕获" },
  { id: "002", label: "02", domain: "CRM", en: "B2B quote & account response", zh: "B2B 报价与客户响应" },
  { id: "003", label: "03", domain: "CRM", en: "Service ticket resolution", zh: "服务工单处理" },
  { id: "004", label: "04", domain: "CRM", en: "Retention & churn analytics", zh: "留存与流失分析" },
  { id: "005", label: "05", domain: "ERP", en: "Finance expense control & close", zh: "费用控制与账务结算" },
  { id: "006", label: "06", domain: "ERP", en: "Procurement, supplier & receiving", zh: "采购、供应商与收货" },
  { id: "007", label: "07", domain: "ERP", en: "Inventory & order fulfillment", zh: "库存与订单履约" },
  { id: "008", label: "08", domain: "Finance", en: "Personal advisory, tax & estate", zh: "个人理财、税务与遗产规划" },
  { id: "009", label: "09", domain: "Finance", en: "Operational modeling & reporting", zh: "运营建模与管理报表" },
  { id: "010", label: "10", domain: "Finance", en: "Investment strategy & portfolio risk", zh: "投资策略与组合风险" },
  { id: "011", label: "11", domain: "Finance", en: "Credit risk & lending committee", zh: "信用风险与信贷委员会" },
  { id: "012", label: "12", domain: "ERP", en: "HR employee lifecycle & policy", zh: "HR 员工生命周期与制度" }
];

export const taskTopics = {
  "001": [
    ["train_001", "Train", "Event sponsor handoff", "Validate event attendance, sponsor status, qualified leads, and the next CRM follow-up."],
    ["train_002", "Train", "Exhibitor lead qualification", "Rank booth leads by fit, urgency, and account context before assigning sales ownership."],
    ["train_003", "Train", "Webinar import cleanup", "Deduplicate imported attendees and reconcile form answers with existing company records."],
    ["train_004", "Train", "Field-day campaign review", "Turn scattered event activity into clean campaign outcomes and follow-up queues."],
    ["train_005", "Train", "Target-account prospecting", "Identify the strongest prospects in a niche segment and prepare CRM-ready outreach notes."],
    ["test_001", "Test", "Executive forum handoff", "Audit a new event pipeline and decide which accounts deserve immediate sales action."],
    ["test_002", "Test", "Partner expo qualification", "Separate real opportunities from lookalike records after a partner-led marketing event."],
    ["test_003", "Test", "Imported lead normalization", "Clean a messy lead import and connect attendees to the right companies and campaigns."],
    ["test_004", "Test", "Industrial demo follow-up", "Reconcile demo attendance, sponsor signals, and account history into follow-up priorities."],
    ["test_005", "Test", "Regional account shortlist", "Build a prioritized prospect list using firmographic clues and recent engagement signals."]
  ],
  "002": [
    ["train_001", "Train", "Renewal quote triage", "Review a customer request and assemble the right quote details from account context."],
    ["train_002", "Train", "Enterprise upsell response", "Check contract terms, usage signals, and open opportunities before drafting a response."],
    ["train_003", "Train", "Procurement email routing", "Classify buyer questions and attach the right commercial owner and next step."],
    ["train_004", "Train", "Discount exception review", "Decide whether a requested discount fits policy, deal stage, and customer history."],
    ["train_005", "Train", "Account expansion brief", "Summarize renewal risk, expansion fit, and quote blockers for the account team."],
    ["test_001", "Test", "Quote revision request", "Resolve a changed scope request while preserving pricing, approval, and CRM consistency."],
    ["test_002", "Test", "Buyer objection response", "Use account records to answer procurement concerns without inventing commercial terms."],
    ["test_003", "Test", "Contract-change handoff", "Find the correct owner and required evidence for a contract or quote adjustment."],
    ["test_004", "Test", "Multi-site account quote", "Combine subsidiary records, seat counts, and timing into a clean quote recommendation."],
    ["test_005", "Test", "Escalation-ready account note", "Prepare a concise response plan for a customer whose quote needs extra approval."]
  ],
  "003": [
    ["train_001", "Train", "Priority ticket routing", "Read a support case and assign severity, owner, and the next customer action."],
    ["train_002", "Train", "SLA breach investigation", "Use ticket history to explain whether a service-level deadline was missed."],
    ["train_003", "Train", "Bug-report consolidation", "Merge related complaints into a clean support summary without losing customer impact."],
    ["train_004", "Train", "Escalation evidence pack", "Collect reproduction steps, account details, and recent support notes for engineering."],
    ["train_005", "Train", "Resolution quality check", "Verify whether a proposed response actually addresses the customer issue."],
    ["test_001", "Test", "Refund-risk support case", "Identify support history, promised actions, and the right path to preserve the account."],
    ["test_002", "Test", "Outage communication draft", "Summarize customer impact and produce a grounded update from service records."],
    ["test_003", "Test", "Duplicate-ticket cleanup", "Find duplicate cases and consolidate status, ownership, and customer-facing commitments."],
    ["test_004", "Test", "Technical escalation triage", "Decide if a case requires engineering escalation and list the missing diagnostics."],
    ["test_005", "Test", "Close-ready ticket audit", "Check whether a ticket can be closed or needs one more customer-confirmed step."]
  ],
  "004": [
    ["train_001", "Train", "At-risk account scan", "Detect churn risk from usage drops, support history, renewal timing, and stakeholder signals."],
    ["train_002", "Train", "Retention playbook selection", "Choose a save motion based on contract value, adoption pattern, and open issues."],
    ["train_003", "Train", "Customer health explanation", "Turn mixed account signals into a clear health score rationale."],
    ["train_004", "Train", "Renewal objection map", "Connect cancellation language to the right product, price, or support concern."],
    ["train_005", "Train", "Win-back segmenting", "Identify which former customers are realistic candidates for reactivation."],
    ["test_001", "Test", "Executive churn brief", "Summarize why a customer may leave and which actions are most time-sensitive."],
    ["test_002", "Test", "Usage-cohort comparison", "Compare similar customers to separate normal seasonality from real disengagement."],
    ["test_003", "Test", "Retention owner assignment", "Route each account to the correct success, sales, or support owner."],
    ["test_004", "Test", "Cancellation pattern review", "Extract repeated churn drivers from a set of recent customer records."],
    ["test_005", "Test", "Save-plan prioritization", "Rank at-risk customers by revenue impact and probability of recovery."]
  ],
  "005": [
    ["train_001", "Train", "Expense-policy audit", "Check employee expenses against category rules, limits, receipts, and approval status."],
    ["train_002", "Train", "Month-end close cleanup", "Find close blockers caused by unmatched invoices, late approvals, or miscoded items."],
    ["train_003", "Train", "Vendor invoice exception", "Resolve invoice mismatches by comparing purchase, receipt, and payment records."],
    ["train_004", "Train", "Card-spend reconciliation", "Match card transactions to employees, projects, and policy-compliant documentation."],
    ["train_005", "Train", "Accrual review", "Identify expenses that should be accrued before the reporting period closes."],
    ["test_001", "Test", "Late expense triage", "Decide which late claims can be approved and which need finance follow-up."],
    ["test_002", "Test", "Close variance explanation", "Explain budget variance using invoices, expense categories, and timing differences."],
    ["test_003", "Test", "Duplicate payment check", "Detect duplicate or suspicious payments across similar vendor records."],
    ["test_004", "Test", "Department spend review", "Summarize spend exceptions for a department head before close."],
    ["test_005", "Test", "Approval-chain repair", "Find missing approvals and route finance items to the correct approver."]
  ],
  "006": [
    ["train_001", "Train", "Purchase-order matching", "Match requested items, POs, receipts, and supplier invoices."],
    ["train_002", "Train", "Supplier onboarding check", "Verify required vendor records, tax forms, risk flags, and payment terms."],
    ["train_003", "Train", "Receiving discrepancy", "Resolve quantity or item mismatches between warehouse receipt and purchase order."],
    ["train_004", "Train", "Vendor performance review", "Compare late deliveries, defect notes, and contract terms for supplier follow-up."],
    ["train_005", "Train", "Emergency reorder decision", "Determine whether a rush purchase is justified by demand and stock status."],
    ["test_001", "Test", "Invoice hold release", "Decide what evidence is needed before releasing a blocked supplier invoice."],
    ["test_002", "Test", "Supplier substitution request", "Evaluate an alternate supplier using price, availability, and compliance context."],
    ["test_003", "Test", "Partial receipt reconciliation", "Update receiving status when only part of a purchase order arrives."],
    ["test_004", "Test", "Procurement exception summary", "Prepare a clean exception list for finance and operations review."],
    ["test_005", "Test", "Contract-term validation", "Check whether a purchasing decision follows negotiated supplier terms."]
  ],
  "007": [
    ["train_001", "Train", "Stockout prevention", "Spot items at risk of stockout and recommend reorder priorities."],
    ["train_002", "Train", "Order allocation review", "Allocate limited inventory across customer orders using priority and due dates."],
    ["train_003", "Train", "Warehouse transfer plan", "Move stock between locations to cover demand without creating new gaps."],
    ["train_004", "Train", "Backorder communication", "Summarize delayed orders and prepare accurate customer-facing status updates."],
    ["train_005", "Train", "Fulfillment exception audit", "Identify orders blocked by address, payment, inventory, or shipping issues."],
    ["test_001", "Test", "Demand spike response", "Decide how to fulfill urgent demand when inventory is split across sites."],
    ["test_002", "Test", "Aged inventory cleanup", "Find slow-moving items and suggest transfer, markdown, or hold actions."],
    ["test_003", "Test", "Shipment priority queue", "Rank open shipments by service level, customer importance, and promised date."],
    ["test_004", "Test", "Inventory count variance", "Explain count differences using recent receipts, shipments, and adjustments."],
    ["test_005", "Test", "Order rescue plan", "Create the next best action for orders that are close to missing fulfillment SLA."]
  ],
  "008": [
    ["train_001", "Train", "Tax-sensitive income review", "Assess income, deductions, and deadlines before recommending planning steps."],
    ["train_002", "Train", "Estate document checklist", "Identify missing estate-planning documents and beneficiary conflicts."],
    ["train_003", "Train", "Retirement cash-flow snapshot", "Summarize assets, spending, and timeline to guide retirement advice."],
    ["train_004", "Train", "Capital-gains planning", "Evaluate realized gains, holding periods, and tax-loss harvesting opportunities."],
    ["train_005", "Train", "Family advisory brief", "Turn scattered household records into an adviser-ready planning memo."],
    ["test_001", "Test", "Year-end tax action list", "Prioritize tax moves before filing or year-end deadlines."],
    ["test_002", "Test", "Trust and beneficiary review", "Spot mismatches between estate wishes, account titling, and beneficiary records."],
    ["test_003", "Test", "Liquidity-needs analysis", "Determine whether planned withdrawals can cover spending without disrupting strategy."],
    ["test_004", "Test", "Charitable giving scenario", "Compare charitable options using tax impact, timing, and portfolio context."],
    ["test_005", "Test", "Adviser meeting prep", "Prepare the key questions and recommendations for a personal finance review."]
  ],
  "009": [
    ["train_001", "Train", "Revenue-forecast refresh", "Update a forecast from actuals, pipeline changes, and seasonality notes."],
    ["train_002", "Train", "Operating KPI deck", "Choose the right metrics and explain movement for a management update."],
    ["train_003", "Train", "Budget variance bridge", "Explain the difference between plan and actuals across drivers."],
    ["train_004", "Train", "Scenario model check", "Evaluate upside and downside assumptions for a business scenario."],
    ["train_005", "Train", "Monthly report QA", "Find inconsistent totals, stale assumptions, and narrative gaps in a report."],
    ["test_001", "Test", "Board metric summary", "Turn operating data into a concise performance narrative for leadership."],
    ["test_002", "Test", "Forecast-risk callout", "Identify which assumptions create the largest risk to the next forecast."],
    ["test_003", "Test", "Department model reconciliation", "Align headcount, spend, and revenue assumptions across operating teams."],
    ["test_004", "Test", "Executive variance note", "Explain a surprising variance without overclaiming from incomplete data."],
    ["test_005", "Test", "Report correction plan", "Prioritize corrections needed before a financial model can be shared."]
  ],
  "010": [
    ["train_001", "Train", "Portfolio risk scan", "Measure concentration, drawdown exposure, and asset-class imbalance."],
    ["train_002", "Train", "Rebalancing recommendation", "Suggest trades that bring a portfolio closer to target allocation."],
    ["train_003", "Train", "Investment memo review", "Compare thesis, risk, valuation, and time horizon before recommending action."],
    ["train_004", "Train", "Stress-scenario summary", "Explain how a portfolio might behave under rate, inflation, or market shocks."],
    ["train_005", "Train", "Manager due-diligence notes", "Summarize performance, fees, mandate fit, and red flags for a fund manager."],
    ["test_001", "Test", "Risk-budget adjustment", "Decide how to adjust exposure when risk budget or client constraints change."],
    ["test_002", "Test", "Portfolio drift diagnosis", "Find which positions caused allocation drift and what to do next."],
    ["test_003", "Test", "Strategy comparison brief", "Compare candidate strategies using return drivers and downside controls."],
    ["test_004", "Test", "Liquidity stress review", "Check whether portfolio liquidity matches expected withdrawal needs."],
    ["test_005", "Test", "Committee-ready recommendation", "Prepare an investment action with supporting risk and rationale."]
  ],
  "011": [
    ["train_001", "Train", "Borrower risk summary", "Review financials, collateral, covenants, and recent performance for credit risk."],
    ["train_002", "Train", "Loan exception triage", "Identify missing documents and policy exceptions before committee review."],
    ["train_003", "Train", "Covenant breach analysis", "Explain whether a borrower has breached terms and what mitigation is needed."],
    ["train_004", "Train", "Lending memo preparation", "Condense borrower strengths, weaknesses, and proposed terms into a committee memo."],
    ["train_005", "Train", "Portfolio watchlist update", "Rank credits by deterioration signals and required monitoring actions."],
    ["test_001", "Test", "Renewal credit review", "Assess whether a loan renewal fits risk appetite and updated borrower data."],
    ["test_002", "Test", "Collateral sufficiency check", "Evaluate collateral coverage under updated values and outstanding exposure."],
    ["test_003", "Test", "Committee question pack", "Prepare likely committee questions from weaknesses in the credit file."],
    ["test_004", "Test", "Risk-rating adjustment", "Decide whether borrower risk rating should change based on new signals."],
    ["test_005", "Test", "Approval-condition drafting", "Write clear conditions needed before credit approval can proceed."]
  ],
  "012": [
    ["train_001", "Train", "Onboarding readiness audit", "Check whether a new hire has the right documents, systems, and manager actions."],
    ["train_002", "Train", "Leave-policy interpretation", "Apply company policy to a leave request with timing and eligibility constraints."],
    ["train_003", "Train", "Compensation-change routing", "Route a pay or role change through the correct approval and record updates."],
    ["train_004", "Train", "Employee-relations case summary", "Summarize a sensitive HR case with facts, dates, and required next steps."],
    ["train_005", "Train", "Offboarding checklist repair", "Find missing offboarding actions across IT, payroll, manager, and compliance."],
    ["test_001", "Test", "Internal transfer review", "Validate transfer eligibility and identify changes needed in HR systems."],
    ["test_002", "Test", "Policy exception decision", "Decide whether an exception request fits documented HR policy and precedent."],
    ["test_003", "Test", "Performance-cycle cleanup", "Identify missing reviews, calibration blockers, and manager follow-ups."],
    ["test_004", "Test", "Benefits enrollment case", "Resolve benefit eligibility and enrollment timing from employee records."],
    ["test_005", "Test", "Termination-risk handoff", "Prepare a compliant handoff for a complex employee exit."]
  ]
};
