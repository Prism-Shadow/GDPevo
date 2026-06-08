const state = {
  module: "dashboard",
  cases: [],
  policies: [],
  selectedCase: null,
  selectedTab: "overview"
};

const titles = {
  dashboard: ["Dashboard", "Shared HR operations workspace"],
  employees: ["Employees", "Directory records from HRMS"],
  recruitment: ["Recruitment", "Openings, candidate outcomes, offers, and follow-up notices"],
  leave: ["Leave", "Leave assignments with source status and balance evidence"],
  payroll: ["Payroll", "Salary assignments, payroll worksheets, and submitted/draft states"],
  cases: ["Policy Cases", "Case queue with approvals, documents, comments, and audit history"],
  documents: ["Documents", "Folder checklists, required files, tags, and attachments"],
  messages: ["Messages", "Formal notices and internal notifications"],
  policies: ["Policy Center", "Current policy documents and source-precedence rules"],
  audit: ["Audit Log", "System events across lifecycle modules"]
};

function qs(selector) {
  return document.querySelector(selector);
}

function qsa(selector) {
  return Array.from(document.querySelectorAll(selector));
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json();
}

function html(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function statusClass(value) {
  return String(value || "")
    .toLowerCase()
    .replaceAll(" ", "-")
    .replace("in-review", "pending")
    .replace("needs-info", "needs")
    .replace("submitted", "pending")
    .replace("high", "high")
    .replace("urgent", "urgent");
}

function badge(value) {
  return `<span class="status ${statusClass(value)}">${html(value)}</span>`;
}

function money(value) {
  return Number(value || 0).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function setModule(module) {
  state.module = module;
  const [title, subtitle] = titles[module];
  qs("#module-title").textContent = title;
  qs("#module-subtitle").textContent = subtitle;
  qsa(".nav-button").forEach((btn) => btn.classList.toggle("active", btn.dataset.module === module));
  qsa(".module").forEach((panel) => panel.classList.toggle("active", panel.id === module));
}

function metric(label, value) {
  return `<div class="metric"><span>${html(label)}</span><strong>${html(value)}</strong></div>`;
}

async function loadDashboard() {
  const summary = await api("/api/summary");
  const cases = await api("/api/cases");
  const policies = await api("/api/policies");
  state.cases = cases;
  state.policies = policies;

  qs("#metrics").innerHTML = [
    metric("Employees", summary.counts.employees),
    metric("Cases", summary.counts.cases),
    metric("Policies", summary.counts.policies),
    metric("Recruiting", summary.counts.recruitment),
    metric("Documents", summary.counts.documents),
    metric("Messages", summary.counts.messages),
    metric("Audit Events", summary.counts.audit_events)
  ].join("");

  const priority = cases
    .filter((item) => ["High", "Urgent"].includes(item.priority) || ["Needs Info", "In Review", "Submitted"].includes(item.status))
    .slice(0, 8);
  qs("#priority-cases").innerHTML = priority
    .map((item) => `
      <article class="item clickable" data-case-id="${html(item.case_id)}">
        <div class="item-title">${html(item.case_id)} - ${html(item.title)}</div>
        <div class="meta">${html(item.employee_name)} - ${html(item.owner)} - due ${html(item.due_at)}</div>
        <div>${badge(item.status)} ${badge(item.priority)}</div>
      </article>
    `)
    .join("");

  qs("#policy-list-short").innerHTML = policies
    .map((policy) => `
      <article class="item clickable" data-policy-id="${html(policy.policy_id)}">
        <div class="item-title">${html(policy.policy_id)} - ${html(policy.title)}</div>
        <div class="meta">${html(policy.owner)} - effective ${html(policy.effective_date)}</div>
      </article>
    `)
    .join("");
}

async function loadCases() {
  const params = new URLSearchParams();
  const query = qs("#case-search").value.trim();
  const status = qs("#case-status").value;
  const type = qs("#case-type").value;
  if (query) params.set("q", query);
  if (status) params.set("status", status);
  if (type) params.set("type", type);
  const cases = await api(`/api/cases?${params}`);
  state.cases = cases;
  qs("#case-table").innerHTML = cases.map((item) => `
    <tr data-case-id="${html(item.case_id)}">
      <td><strong>${html(item.case_id)}</strong><br><span class="meta">${html(item.title)}</span></td>
      <td>${html(item.employee_name)}<br><span class="meta">${html(item.employee_id)}</span></td>
      <td>${html(item.case_type)}</td>
      <td>${badge(item.status)}</td>
      <td>${badge(item.priority)}</td>
      <td>${html(item.owner)}</td>
      <td>${html(item.due_at)}</td>
    </tr>
  `).join("");
}

async function loadEmployees() {
  const params = new URLSearchParams();
  const query = qs("#employee-search").value.trim();
  const status = qs("#employee-status").value;
  if (query) params.set("q", query);
  if (status) params.set("status", status);
  const employees = await api(`/api/employees?${params}`);
  qs("#employee-grid").innerHTML = employees.map((emp) => `
    <article class="employee-card">
      <strong>${html(emp.name)}</strong>
      <div class="meta">${html(emp.employee_id)} - ${html(emp.email)}</div>
      <p>${html(emp.designation)} - ${html(emp.department)}</p>
      <div>${badge(emp.status)} ${badge(emp.remote_profile)}</div>
      <p class="meta">Manager: ${html(emp.manager)} - Location: ${html(emp.location)} - Leave: ${html(emp.leave_balance_days)} days</p>
    </article>
  `).join("");
}

async function loadPolicies() {
  const params = new URLSearchParams();
  const query = qs("#policy-search").value.trim();
  if (query) params.set("q", query);
  const policies = await api(`/api/policies?${params}`);
  state.policies = policies;
  qs("#policy-grid").innerHTML = policies.map((policy) => `
    <article class="policy-card" data-policy-id="${html(policy.policy_id)}">
      <strong>${html(policy.policy_id)} - ${html(policy.title)}</strong>
      <p>${html(policy.summary)}</p>
      <div class="meta">${html(policy.owner)} - effective ${html(policy.effective_date)} - ${html(policy.status)}</div>
    </article>
  `).join("");
}

async function loadRecruitment() {
  const params = new URLSearchParams();
  const query = qs("#recruitment-search").value.trim();
  if (query) params.set("q", query);
  const openings = await api(`/api/recruitment?${params}`);
  qs("#recruitment-list").innerHTML = openings.map((row) => `
    <article class="item">
      <div class="item-title">${html(row.opening_id)} - ${html(row.title)}</div>
      <div class="meta">${html(row.status || "Open")} - ${html(row.candidates?.length || 0)} candidates - ${html(row.cost_ledger?.length || 0)} cost lines - ${html(row.notice_packets?.length || 0)} notice packets</div>
      <p>Use candidate review, offer register, cost ledger, notice inspection, and audit detail before routing follow-up.</p>
      <div class="business-actions">
        <button class="button small" data-case-id="${html(row.opening_id)}">Open recruitment case</button>
        <button class="button small" data-recruitment-action="candidates" data-opening-id="${html(row.opening_id)}">Review candidates</button>
        <button class="button small" data-recruitment-action="offers" data-opening-id="${html(row.opening_id)}">Open offer register</button>
        <button class="button small" data-recruitment-action="costs" data-opening-id="${html(row.opening_id)}">Open cost ledger</button>
        <button class="button small" data-recruitment-action="notices" data-opening-id="${html(row.opening_id)}">Inspect notices</button>
        ${row.audit_event_id ? `<button class="button small" data-audit-id="${html(row.audit_event_id)}">Review audit event</button>` : ""}
      </div>
    </article>
  `).join("");
}

async function loadLeave() {
  const params = new URLSearchParams();
  const query = qs("#leave-search").value.trim();
  if (query) params.set("q", query);
  const rows = (await api(`/api/payroll-ledgers?${params}`)).filter((row) => row.record_type.includes("Leave"));
  qs("#leave-table").innerHTML = rows.map((row) => `
    <tr>
      <td><strong>${html(row.ledger_id)}</strong></td>
      <td>${html(row.employee_name)}<br><span class="meta">${html(row.employee_id)}</span></td>
      <td>${badge(row.status)}</td>
      <td>${html(row.period)}</td>
      <td>${html(row.approved_leave_days)}</td>
      <td>${html(row.worksheet_leave_days)}</td>
      <td>${html(row.updated_at)}<br><span class="meta">${html(row.policy_name || "")}</span></td>
    </tr>
  `).join("");
}

async function loadLedgers() {
  const params = new URLSearchParams();
  const query = qs("#ledger-search").value.trim();
  const status = qs("#ledger-status").value;
  if (query) params.set("q", query);
  if (status) params.set("status", status);
  const ledgers = await api(`/api/payroll-ledgers?${params}`);
  qs("#ledger-table").innerHTML = ledgers.map((row) => `
    <tr>
      <td><strong>${html(row.ledger_id)}</strong></td>
      <td>${html(row.employee_name)}<br><span class="meta">${html(row.employee_id)}</span></td>
      <td>${html(row.record_type)}</td>
      <td>${badge(row.status)}</td>
      <td>${html(row.period)}</td>
      <td>${html(row.approved_leave_days)}</td>
      <td>${html(row.worksheet_leave_days)}</td>
      <td>${html(row.updated_at)}<br><span class="meta">${html(row.policy_name || (row.base_salary ? `Base ${money(row.base_salary)}` : ""))}</span></td>
    </tr>
  `).join("");
}

async function loadMessages() {
  const params = new URLSearchParams();
  const query = qs("#message-search").value.trim();
  if (query) params.set("q", query);
  const rows = await api(`/api/messages?${params}`);
  qs("#message-list").innerHTML = rows.map((row) => `
    <article class="item">
      <div class="item-title">${html(row.subject)}</div>
      <div class="meta">${html(row.message_id)} - ${html(row.channel)} - ${html(row.recipient)} - ${html(row.sent_at)}</div>
      <p>Formal notice preview is available through inspection.</p>
      <div>${badge(row.status)} ${badge(row.quality || "review")}
        <button class="button small" data-message-id="${html(row.message_id)}">Inspect notice</button>
        <button class="button small" data-case-id="${html(row.case_id)}">Open Case</button>
      </div>
    </article>
  `).join("");
}

async function loadDocuments() {
  const params = new URLSearchParams();
  const query = qs("#document-search").value.trim();
  if (query) params.set("q", query);
  const rows = await api(`/api/documents?${params}`);
  qs("#document-list").innerHTML = rows.map((row) => {
    return `
      <article class="item">
        <div class="item-title">${html(row.document_id)} - ${html(row.title)}</div>
        <div class="meta">${html(row.files.length)} filed files - ${html(row.required_files.length)} required files - ${html(row.tags.length)} current tags</div>
        <p>Open the checklist to compare required evidence against the filed folder contents.</p>
        <div>${badge(row.ready ? "Ready" : "Not ready")} <button class="button small" data-doc-preview="${html(row.document_id)}">Open folder checklist</button></div>
      </article>
    `;
  }).join("");
}

async function loadAudit() {
  const params = new URLSearchParams();
  const query = qs("#audit-search").value.trim();
  if (query) params.set("q", query);
  const rows = await api(`/api/audit?${params}`);
  qs("#audit-table").innerHTML = rows.map((row) => `
    <tr data-audit-id="${html(row.audit_id)}">
      <td><strong>${html(row.audit_id)}</strong></td>
      <td>${html(row.timestamp)}</td>
      <td>${html(row.case_id)}</td>
      <td>${html(row.actor)}</td>
      <td>${html(row.event)}</td>
      <td>${html(row.source)}</td>
    </tr>
  `).join("");
}

async function refreshCurrent() {
  if (state.module === "dashboard") return loadDashboard();
  if (state.module === "cases") return loadCases();
  if (state.module === "employees") return loadEmployees();
  if (state.module === "recruitment") return loadRecruitment();
  if (state.module === "leave") return loadLeave();
  if (state.module === "policies") return loadPolicies();
  if (state.module === "payroll") return loadLedgers();
  if (state.module === "documents") return loadDocuments();
  if (state.module === "messages") return loadMessages();
  if (state.module === "audit") return loadAudit();
}

async function openCase(caseId) {
  const caseData = await api(`/api/cases/${encodeURIComponent(caseId)}`);
  state.selectedCase = caseData;
  state.selectedTab = "overview";
  qs("#drawer-kicker").textContent = `${caseData.case_id} - ${caseData.case_type}`;
  qs("#drawer-title").textContent = caseData.title;
  qsa(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === "overview"));
  qs("#case-drawer").classList.add("open");
  qs("#case-drawer").setAttribute("aria-hidden", "false");
  renderDrawer();
}

function field(label, value) {
  return `<div class="field"><span>${html(label)}</span><strong>${html(value)}</strong></div>`;
}

function renderDrawer() {
  const item = state.selectedCase;
  if (!item) return;
  const target = qs("#drawer-content");

  if (state.selectedTab === "overview") {
    target.innerHTML = `
      <div class="detail-grid">
        ${field("Employee", `${item.employee_name} (${item.employee_id})`)}
        ${field("Department", item.department)}
        ${field("Status", item.status)}
        ${field("Priority", item.priority)}
        ${field("Owner", item.owner)}
        ${field("Due", item.due_at)}
        ${field("Opened", item.opened_at)}
        ${field("Policy References", item.policy_refs.join(", "))}
      </div>
      <p>${html(item.summary)}</p>
      <div class="business-actions">
        ${item.policy_refs.map((id) => `<button class="button small" data-policy-id="${html(id)}">View ${html(id)}</button>`).join("")}
      </div>
    `;
    return;
  }

  if (state.selectedTab === "approvals") {
    target.innerHTML = `<div class="timeline">${item.approvals.map((approval) => `
      <article class="timeline-item">
        <strong>${html(approval.step)} - ${badge(approval.decision)}</strong>
        <p>${html(approval.note)}</p>
        <div class="meta">${html(approval.approver)} - ${html(approval.decided_at || "Pending")}</div>
      </article>
    `).join("")}</div>`;
    return;
  }

  if (state.selectedTab === "comments") {
    target.innerHTML = `
      <form id="comment-form" class="comment-box">
        <strong>Add case comment</strong>
        <input name="author" placeholder="Author" value="Portal User">
        <select name="visibility">
          <option>Internal</option>
          <option>Manager-visible</option>
          <option>Employee-visible</option>
        </select>
        <textarea name="body" placeholder="Comment body"></textarea>
        <button class="button" type="submit">Post Comment</button>
      </form>
      <div class="timeline">${item.comments.map((comment) => `
        <article class="timeline-item">
          <strong>${html(comment.author)} - ${badge(comment.visibility)}</strong>
          <p>${html(comment.body)}</p>
          <div class="meta">${html(comment.comment_id)} - ${html(comment.created_at)}</div>
        </article>
      `).join("")}</div>
    `;
    qs("#comment-form").addEventListener("submit", postComment);
    return;
  }

  if (state.selectedTab === "attachments") {
    target.innerHTML = `<div class="list">${item.attachments.map((attachment) => `
      <article class="item">
        <div class="item-title">${html(attachment.name)}</div>
        <div class="meta">${html(attachment.attachment_id)} - ${html(attachment.kind)} - ${html(attachment.uploaded_by)} - ${html(attachment.uploaded_at)}</div>
        <div>${badge(attachment.status)} <button class="button small" data-attachment-id="${html(attachment.attachment_id)}">Open Attachment</button></div>
      </article>
    `).join("")}</div>`;
    return;
  }

  if (state.selectedTab === "audit-detail") {
    target.innerHTML = `<div class="timeline">${item.audit_events.map((event) => `
      <article class="timeline-item">
        <strong>${html(event.audit_id)} - ${html(event.event)}</strong>
        <p>${html(event.detail)}</p>
        <div class="meta">${html(event.actor)} - ${html(event.source)} - ${html(event.timestamp)}</div>
        <button class="button small" data-audit-id="${html(event.audit_id)}">Open Audit Detail</button>
      </article>
    `).join("")}</div>`;
  }
}

async function postComment(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const body = {
    author: form.get("author"),
    visibility: form.get("visibility"),
    body: form.get("body")
  };
  await api(`/api/cases/${encodeURIComponent(state.selectedCase.case_id)}/comments`, {
    method: "POST",
    body: JSON.stringify(body)
  });
  await openCase(state.selectedCase.case_id);
  state.selectedTab = "comments";
  qsa(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === "comments"));
  renderDrawer();
}

function openModal(title, body) {
  qs("#modal-title").textContent = title;
  qs("#modal-body").innerHTML = body;
  qs("#modal-backdrop").hidden = false;
  qs("#modal").hidden = false;
}

function closeModal() {
  qs("#modal-backdrop").hidden = true;
  qs("#modal").hidden = true;
}

async function openPolicy(policyId) {
  const policies = policyId ? [await api(`/api/policies/${encodeURIComponent(policyId)}`)] : await api("/api/policies");
  openModal("Policy Viewer", policies.map((policy) => `
    <article class="policy-section">
      <h4>${html(policy.policy_id)} - ${html(policy.title)}</h4>
      <p>${html(policy.summary)}</p>
      <div class="meta">${html(policy.owner)} - effective ${html(policy.effective_date)} - ${html(policy.status)}</div>
      ${policy.sections.map((section) => `
        <section class="policy-section">
          <h4>${html(section.heading)}</h4>
          <p>${html(section.body)}</p>
        </section>
      `).join("")}
    </article>
  `).join(""));
}

async function openAttachment(attachmentId) {
  const res = await fetch(`/api/attachments/${encodeURIComponent(attachmentId)}`);
  const text = await res.text();
  openModal(`Attachment ${attachmentId}`, `<pre>${html(text)}</pre>`);
}

async function openAudit(auditId) {
  const event = await api(`/api/audit/${encodeURIComponent(auditId)}`);
  openModal(`Audit Detail ${auditId}`, `
    <div class="detail-grid">
      ${field("Audit ID", event.audit_id)}
      ${field("Case", event.case_id)}
      ${field("Employee", event.employee_id)}
      ${field("Timestamp", event.timestamp)}
      ${field("Actor", event.actor)}
      ${field("Event", event.event)}
      ${field("Source", event.source)}
    </div>
    <p>${html(event.detail)}</p>
  `);
}

async function openRecruitmentPanel(openingId, panel) {
  const rows = await api(`/api/recruitment?q=${encodeURIComponent(openingId)}`);
  const row = rows.find((item) => item.opening_id === openingId);
  if (!row) {
    openModal("Recruitment Review", `<p>No opening found for ${html(openingId)}.</p>`);
    return;
  }
  if (panel === "candidates") {
    openModal(`Candidate Review ${openingId}`, `
      <div class="timeline">${(row.candidates || []).map((candidate) => `
        <article class="timeline-item">
          <strong>${html(candidate.candidate_id)} - ${html(candidate.name)}</strong>
          <p>${html(candidate.pipeline_stage)} - committee decision: ${html(candidate.committee_decision)} - notice: ${html(candidate.notice_status)}</p>
          <div class="meta">Interview rounds: ${html((candidate.rounds || []).join(", "))}</div>
        </article>
      `).join("")}</div>
    `);
    return;
  }
  if (panel === "offers") {
    openModal(`Offer Register ${openingId}`, `
      <div class="timeline">${(row.offer_register || []).map((offer) => `
        <article class="timeline-item">
          <strong>${html(offer.offer_id)} - ${html(offer.candidate_id)}</strong>
          <p>Status: ${html(offer.status)} - base salary: ${html(money(offer.base_salary))}</p>
        </article>
      `).join("") || "<p>No offer records.</p>"}</div>
      <h4>Payroll Precheck Records</h4>
      <div class="timeline">${(row.payroll_precheck_records || []).map((record) => `
        <article class="timeline-item">
          <strong>${html(record.record_id)} - ${badge(record.status)}</strong>
          <p>${html(record.candidate_id)} - ${html(record.note)}</p>
        </article>
      `).join("") || "<p>No payroll precheck records.</p>"}</div>
    `);
    return;
  }
  if (panel === "costs") {
    const total = (row.cost_ledger || []).reduce((sum, line) => sum + Number(line.amount || 0), 0);
    openModal(`Cost Ledger ${openingId}`, `
      <div class="timeline">${(row.cost_ledger || []).map((line) => `
        <article class="timeline-item">
          <strong>${html(line.line_id)}</strong>
          <p>${html(line.label)} - ${html(money(line.amount))}</p>
        </article>
      `).join("")}</div>
      <div class="metric"><span>Ledger total</span><strong>${html(money(total))}</strong></div>
    `);
    return;
  }
  if (panel === "notices") {
    openModal(`Notice Review ${openingId}`, `
      <div class="timeline">${(row.notice_packets || []).map((notice) => `
        <article class="timeline-item">
          <strong>${html(notice.candidate_id)} - ${html(notice.notice_type)}</strong>
          <p>Status: ${html(notice.status)} - quality: ${html(notice.quality || "pending")}</p>
          <div class="meta">Defects: ${html((notice.defects || []).join(", ") || "none")} - action: ${html(notice.required_action || "none")}</div>
          ${notice.message_id ? `<button class="button small" data-message-id="${html(notice.message_id)}">Open message</button>` : ""}
        </article>
      `).join("") || "<p>No notice packets.</p>"}</div>
    `);
  }
}

async function openDocumentChecklist(documentId) {
  const rows = await api(`/api/documents?q=${encodeURIComponent(documentId)}`);
  const row = rows.find((item) => item.document_id === documentId);
  if (!row) {
    openModal(`Folder Checklist ${documentId}`, `<p>No document folder found.</p>`);
    return;
  }
  const missingFiles = row.required_files.filter((file) => !row.files.includes(file));
  const missingTags = row.required_tags.filter((tag) => !row.tags.includes(tag));
  openModal(`Folder Checklist ${documentId}`, `
    <div class="detail-grid">
      ${field("Required files", row.required_files.join(", ") || "none")}
      ${field("Filed files", row.files.join(", ") || "none")}
      ${field("Missing files", missingFiles.join(", ") || "none")}
      ${field("Required tags", row.required_tags.join(", ") || "none")}
      ${field("Current tags", row.tags.join(", ") || "none")}
      ${field("Missing tags", missingTags.join(", ") || "none")}
    </div>
  `);
}

async function openMessage(messageId) {
  const rows = await api(`/api/messages?q=${encodeURIComponent(messageId)}`);
  const row = rows.find((item) => item.message_id === messageId);
  if (!row) {
    openModal(`Notice ${messageId}`, `<p>No message found.</p>`);
    return;
  }
  openModal(`Notice Inspection ${messageId}`, `
    <div class="detail-grid">
      ${field("Case", row.case_id)}
      ${field("Recipient", row.recipient)}
      ${field("Status", row.status)}
      ${field("Quality", row.quality || "review")}
      ${field("Defects", (row.defects || []).join(", ") || "none")}
    </div>
    <p>${html(row.body || "")}</p>
  `);
}

function wireEvents() {
  qsa(".nav-button").forEach((btn) => btn.addEventListener("click", async () => {
    setModule(btn.dataset.module);
    await refreshCurrent();
  }));
  qsa("[data-jump]").forEach((btn) => btn.addEventListener("click", async () => {
    setModule(btn.dataset.jump);
    await refreshCurrent();
  }));
  qs("#refresh-button").addEventListener("click", refreshCurrent);
  qs("#open-policy-button").addEventListener("click", () => openPolicy());
  qs("#drawer-close").addEventListener("click", () => {
    qs("#case-drawer").classList.remove("open");
    qs("#case-drawer").setAttribute("aria-hidden", "true");
  });
  qsa(".tab").forEach((tab) => tab.addEventListener("click", () => {
    state.selectedTab = tab.dataset.tab;
    qsa(".tab").forEach((item) => item.classList.toggle("active", item === tab));
    renderDrawer();
  }));
  qs("#modal-close").addEventListener("click", closeModal);
  qs("#modal-backdrop").addEventListener("click", closeModal);

  qs("#case-filter").addEventListener("click", loadCases);
  qs("#employee-filter").addEventListener("click", loadEmployees);
  qs("#recruitment-filter").addEventListener("click", loadRecruitment);
  qs("#leave-filter").addEventListener("click", loadLeave);
  qs("#policy-filter").addEventListener("click", loadPolicies);
  qs("#ledger-filter").addEventListener("click", loadLedgers);
  qs("#document-filter").addEventListener("click", loadDocuments);
  qs("#message-filter").addEventListener("click", loadMessages);
  qs("#audit-filter").addEventListener("click", loadAudit);

  document.body.addEventListener("click", async (event) => {
    const caseTarget = event.target.closest("[data-case-id]");
    const policyTarget = event.target.closest("[data-policy-id]");
    const attachmentTarget = event.target.closest("[data-attachment-id]");
    const auditTarget = event.target.closest("[data-audit-id]");
    const docPreviewTarget = event.target.closest("[data-doc-preview]");
    const recruitmentTarget = event.target.closest("[data-recruitment-action]");
    const messageTarget = event.target.closest("[data-message-id]");
    const actionTarget = event.target.closest("[data-action]");

    if (messageTarget) {
      await openMessage(messageTarget.dataset.messageId);
      return;
    }
    if (recruitmentTarget) {
      await openRecruitmentPanel(recruitmentTarget.dataset.openingId, recruitmentTarget.dataset.recruitmentAction);
      return;
    }
    if (attachmentTarget) {
      await openAttachment(attachmentTarget.dataset.attachmentId);
      return;
    }
    if (auditTarget) {
      await openAudit(auditTarget.dataset.auditId);
      return;
    }
    if (docPreviewTarget) {
      await openDocumentChecklist(docPreviewTarget.dataset.docPreview);
      return;
    }
    if (policyTarget) {
      await openPolicy(policyTarget.dataset.policyId);
      return;
    }
    if (caseTarget) {
      await openCase(caseTarget.dataset.caseId);
      return;
    }
    if (actionTarget && state.selectedCase) {
      const labels = {
        assign: "Reviewer assignment",
        request: "Information request",
        approve: "Approval recording"
      };
      openModal(labels[actionTarget.dataset.action], `
        <p>${html(labels[actionTarget.dataset.action])} action is available for ${html(state.selectedCase.case_id)}.</p>
        <p class="meta">This local portal records comments through the Comments tab and displays existing workflow state for review.</p>
      `);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeModal();
      qs("#case-drawer").classList.remove("open");
    }
  });
}

async function init() {
  wireEvents();
  await loadDashboard();
  await loadCases();
  await loadEmployees();
  await loadRecruitment();
  await loadLeave();
  await loadPolicies();
  await loadLedgers();
  await loadDocuments();
  await loadMessages();
  await loadAudit();
  setModule("dashboard");
}

init().catch((err) => {
  document.body.innerHTML = `<main class="main"><div class="empty">Portal failed to load: ${html(err.message)}</div></main>`;
});
