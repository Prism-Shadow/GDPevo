#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from pathlib import Path


SEED = 12012
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"


def write(name: str, payload) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / name).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def mk_employee(idx: int, dept: str) -> dict:
    first = ["Avery", "Blair", "Camila", "Dev", "Hana", "Isha", "Jules", "Kai", "Mara", "Nina"]
    last = ["Patel", "Chen", "Rao", "Morgan", "Wong", "Diaz", "Brooks", "Kim", "Novak", "Shah"]
    name = f"{random.choice(first)} {random.choice(last)}"
    return {
        "employee_id": f"EMP-{300 + idx}",
        "name": name,
        "email": name.lower().replace(" ", ".") + "@northwind-people.example",
        "department": dept,
        "department_id": f"D-{100 + idx % 9}",
        "designation": random.choice(
            ["People Partner", "Engineer", "Payroll Analyst", "Recruiter", "Operations Analyst"]
        ),
        "division": random.choice(["Chief People Office", "Product and Technology", "Finance"]),
        "employment_type": "Full-time",
        "hire_date": f"2026-0{random.randint(1, 6)}-{random.randint(10, 28)}",
        "leave_balance_days": round(random.uniform(4, 24), 1),
        "location": random.choice(["Boston", "Remote-US", "Chicago", "Denver", "Austin"]),
        "manager": random.choice(["Priya Patel", "Theo Tran", "Alicia Ames", "Hana Hart"]),
        "remote_profile": random.choice(["Hybrid", "Office-first", "Exception pending"]),
        "salary_band": random.choice(["B3", "B4", "M1"]),
        "status": random.choice(["Active", "Onboarding", "Leave", "Active"]),
    }


def case(
    case_id: str,
    title: str,
    employee_id: str,
    employee_name: str,
    case_type: str,
    status: str,
    priority: str,
    owner: str,
    summary: str,
    approvals: list[dict],
    attachments: list[dict],
    audit_events: list[dict],
    comments: list[dict],
    policies: list[str],
) -> dict:
    return {
        "case_id": case_id,
        "title": title,
        "case_type": case_type,
        "status": status,
        "priority": priority,
        "opened_at": "2026-05-21T10:20",
        "due_at": "2026-06-05T17:00",
        "employee_id": employee_id,
        "employee_name": employee_name,
        "department": "People Ops" if case_type == "Recruiting pipeline" else "R&D",
        "owner": owner,
        "policy_refs": policies,
        "summary": summary,
        "approvals": approvals,
        "attachments": attachments,
        "audit_events": audit_events,
        "comments": comments,
    }


def main() -> None:
    random.seed(SEED)
    departments = [
        {"department_id": "D-101", "name": "People Ops", "leader": "Theo Tran"},
        {"department_id": "D-102", "name": "R&D", "leader": "Priya Patel"},
        {"department_id": "D-103", "name": "Engineering", "leader": "Alicia Ames"},
        {"department_id": "D-104", "name": "Finance Systems", "leader": "Hana Hart"},
        {"department_id": "D-105", "name": "Recruiting", "leader": "Blair Stone"},
    ]
    employees = [
        {
            "employee_id": "EMP-104",
            "name": "Mira Chen",
            "email": "mira.chen@northwind-people.example",
            "department": "Engineering",
            "department_id": "D-103",
            "designation": "Platform Engineer",
            "division": "Product and Technology",
            "employment_type": "Full-time",
            "hire_date": "2026-03-01",
            "leave_balance_days": 18,
            "location": "Boston",
            "manager": "Alicia Ames",
            "remote_profile": "Hybrid",
            "salary_band": "B4",
            "status": "Onboarding",
        },
        {
            "employee_id": "EMP-118",
            "name": "Nadia Brooks",
            "email": "nadia.brooks@northwind-people.example",
            "department": "Customer Success",
            "department_id": "D-106",
            "designation": "CS Lead",
            "division": "Revenue",
            "employment_type": "Full-time",
            "hire_date": "2025-08-14",
            "leave_balance_days": 16,
            "location": "Chicago",
            "manager": "Theo Tran",
            "remote_profile": "Hybrid",
            "salary_band": "M1",
            "status": "Active",
        },
        {
            "employee_id": "EMP-122",
            "name": "Omar Patel",
            "email": "omar.patel@northwind-people.example",
            "department": "Finance Systems",
            "department_id": "D-104",
            "designation": "ERP Analyst",
            "division": "Finance",
            "employment_type": "Full-time",
            "hire_date": "2026-04-01",
            "leave_balance_days": 12,
            "location": "Austin",
            "manager": "Hana Hart",
            "remote_profile": "Office-first",
            "salary_band": "B3",
            "status": "Active",
        },
        {
            "employee_id": "EMP-255",
            "name": "Erin Novak",
            "email": "erin.novak@northwind-people.example",
            "department": "R&D",
            "department_id": "D-102",
            "designation": "Senior Research Engineer",
            "division": "Product and Technology",
            "employment_type": "Full-time",
            "hire_date": "2024-08-19",
            "leave_balance_days": 21,
            "location": "Remote-US",
            "manager": "Priya Patel",
            "remote_profile": "Exception pending",
            "salary_band": "B4",
            "status": "Active",
        },
    ]
    employees.extend(mk_employee(i, random.choice([d["name"] for d in departments])) for i in range(40))

    policies = [
        {
            "policy_id": "HR-POL-014",
            "title": "Remote Work Policy",
            "owner": "Legal Desk",
            "effective_date": "2026-01-01",
            "status": "Active",
            "summary": "Remote-work jurisdiction, exception, and notice requirements.",
            "sections": [
                {
                    "heading": "4.2 Domestic jurisdiction",
                    "body": "Remote work is limited to approved domestic tax jurisdictions unless an exception is approved.",
                },
                {
                    "heading": "7.1 Executive exceptions",
                    "body": "International exceptions require executive approval, time limits, tax equalization, VPN-only access, quarterly compliance review, appeal instructions, and acknowledgement deadline in the formal notice.",
                },
            ],
        },
        {
            "policy_id": "LEAVE-SRC-001",
            "title": "Leave Source Precedence",
            "owner": "People Ops",
            "effective_date": "2026-01-01",
            "status": "Active",
            "summary": "Latest approved/submitted assignment controls leave entitlement.",
            "sections": [
                {
                    "heading": "2.1 Assignment source",
                    "body": "The latest approved or submitted leave assignment for the period controls. Draft, voided, and obsolete records are excluded even when profile summaries conflict.",
                }
            ],
        },
        {
            "policy_id": "PAY-SRC-001",
            "title": "Payroll Assignment Source",
            "owner": "Payroll",
            "effective_date": "2026-01-01",
            "status": "Active",
            "summary": "Current submitted salary assignment controls base salary.",
            "sections": [
                {
                    "heading": "3.4 Submitted salary source",
                    "body": "Use the current submitted salary assignment. Draft planning assignments do not affect payroll readiness or accrual checks.",
                },
                {
                    "heading": "4.2 Recruiting handoff gate",
                    "body": "Recruiting payroll handoff is created only after a selected candidate has an accepted offer. The handoff must be submitted; draft prechecks do not satisfy the assignment gate.",
                },
            ],
        },
        {
            "policy_id": "POL-DOCS-2026",
            "title": "Lifecycle Folder Checklist",
            "owner": "Records",
            "effective_date": "2026-01-01",
            "status": "Active",
            "summary": "Required files and tags for lifecycle case folders.",
            "sections": [
                {
                    "heading": "5.1 Required evidence",
                    "body": "A folder is not ready unless all required files and required tags shown in the folder checklist are present.",
                }
            ],
        },
    ]

    documents = [
        {
            "document_id": "DOC-RW-221",
            "title": "Exception-Case-RW-221",
            "required_files": ["request-summary.txt", "decision-record.txt", "tax-equalization-agreement.pdf"],
            "files": ["request-summary.txt", "decision-record.txt"],
            "required_tags": ["PolicyException2026"],
            "tags": ["PolicyException2026"],
            "ready": False,
        },
        {
            "document_id": "DOC-ERIN-ONB",
            "title": "Erin Novak Lifecycle Folder",
            "required_files": [
                "request-summary.txt",
                "benefits-election.pdf",
                "manager-endorsement.pdf",
                "executive-exception-approval.pdf",
            ],
            "files": ["request-summary.txt", "manager-endorsement.pdf"],
            "required_tags": ["Onboarding2026", "PolicyException2026"],
            "tags": ["Onboarding2026"],
            "ready": False,
        },
        {
            "document_id": "DOC-PRIYA-POL",
            "title": "Priya/Nadia Policy Folder",
            "required_files": ["request-summary.txt", "decision-record.txt"],
            "files": ["request-summary.txt"],
            "required_tags": ["PolicyException2026"],
            "tags": [],
            "ready": False,
        },
        {
            "document_id": "DOC-MARCO-PAY",
            "title": "Marco Payroll Folder",
            "required_files": ["payroll-precheck.pdf"],
            "files": ["payroll-precheck.pdf"],
            "required_tags": ["PayrollReady"],
            "tags": ["PayrollReady"],
            "ready": True,
        },
    ]

    payroll_ledgers = [
        {
            "ledger_id": "LA-104-2026-A",
            "employee_id": "EMP-104",
            "employee_name": "Mira Chen",
            "record_type": "Leave assignment",
            "status": "Superseded",
            "period": "2026",
            "approved_leave_days": 16,
            "worksheet_leave_days": 16,
            "updated_at": "2026-01-01T09:00",
            "policy_name": "Engineering Standard Leave 2026",
        },
        {
            "ledger_id": "LA-104-2026-B",
            "employee_id": "EMP-104",
            "employee_name": "Mira Chen",
            "record_type": "Leave assignment",
            "status": "Approved",
            "period": "2026",
            "approved_leave_days": 18,
            "worksheet_leave_days": 18,
            "updated_at": "2026-03-01T09:00",
            "policy_name": "Engineering Flex Leave 2026",
        },
        {
            "ledger_id": "LA-104-2026-DRAFT",
            "employee_id": "EMP-104",
            "employee_name": "Mira Chen",
            "record_type": "Leave assignment",
            "status": "Draft",
            "period": "2026",
            "approved_leave_days": 20,
            "worksheet_leave_days": 20,
            "updated_at": "2026-05-01T09:00",
            "policy_name": "Engineering Draft Leave 2026",
        },
        {
            "ledger_id": "LA-118-APP-02",
            "employee_id": "EMP-118",
            "employee_name": "Nadia Brooks",
            "record_type": "Leave assignment",
            "status": "Approved",
            "period": "2026",
            "approved_leave_days": 16,
            "worksheet_leave_days": 16,
            "updated_at": "2026-02-01T09:00",
            "policy_name": "Customer Success Standard 2026",
        },
        {
            "ledger_id": "LA-255-APP-03",
            "employee_id": "EMP-255",
            "employee_name": "Erin Novak",
            "record_type": "Leave assignment",
            "status": "Approved",
            "period": "2026",
            "approved_leave_days": 21,
            "worksheet_leave_days": 21,
            "updated_at": "2026-04-15T09:00",
            "policy_name": "R&D Flex Leave 2026",
        },
        {
            "ledger_id": "PAY-104-2026-SUB",
            "employee_id": "EMP-104",
            "employee_name": "Mira Chen",
            "record_type": "Salary assignment",
            "status": "Submitted",
            "period": "2026-03",
            "approved_leave_days": 0,
            "worksheet_leave_days": 0,
            "updated_at": "2026-03-01T09:30",
            "base_salary": 128000,
        },
        {
            "ledger_id": "PAY-104-2026-DRAFT",
            "employee_id": "EMP-104",
            "employee_name": "Mira Chen",
            "record_type": "Salary assignment",
            "status": "Draft",
            "period": "2026-05",
            "approved_leave_days": 0,
            "worksheet_leave_days": 0,
            "updated_at": "2026-05-01T09:30",
            "base_salary": 132000,
        },
        {
            "ledger_id": "PAY-122-SUB-03",
            "employee_id": "EMP-122",
            "employee_name": "Omar Patel",
            "record_type": "Salary assignment",
            "status": "Submitted",
            "period": "2026-04",
            "approved_leave_days": 0,
            "worksheet_leave_days": 0,
            "updated_at": "2026-04-01T09:30",
            "base_salary": 98000,
            "accrual_batch_id": "ACCR-2026-04-B",
        },
        {
            "ledger_id": "PAY-122-DRAFT-04",
            "employee_id": "EMP-122",
            "employee_name": "Omar Patel",
            "record_type": "Salary assignment",
            "status": "Draft",
            "period": "2026-05",
            "approved_leave_days": 0,
            "worksheet_leave_days": 0,
            "updated_at": "2026-05-01T09:30",
            "base_salary": 104000,
        },
        {
            "ledger_id": "PAY-255-SUB-02",
            "employee_id": "EMP-255",
            "employee_name": "Erin Novak",
            "record_type": "Salary assignment",
            "status": "Submitted",
            "period": "2026-04",
            "approved_leave_days": 0,
            "worksheet_leave_days": 0,
            "updated_at": "2026-04-15T09:30",
            "base_salary": 142000,
        },
        {
            "ledger_id": "PAY-255-DRAFT-03",
            "employee_id": "EMP-255",
            "employee_name": "Erin Novak",
            "record_type": "Salary assignment",
            "status": "Draft",
            "period": "2026-06",
            "approved_leave_days": 0,
            "worksheet_leave_days": 0,
            "updated_at": "2026-06-01T09:30",
            "base_salary": 149000,
        },
    ]
    for i in range(50):
        emp = random.choice(employees)
        payroll_ledgers.append(
            {
                "ledger_id": f"LED-{i:03d}",
                "employee_id": emp["employee_id"],
                "employee_name": emp["name"],
                "record_type": random.choice(["HRMS leave ledger", "Payroll worksheet", "People Ops adjustment"]),
                "status": random.choice(["Approved", "Submitted", "Draft", "Superseded"]),
                "period": f"2026-0{random.randint(3, 6)}",
                "approved_leave_days": round(random.uniform(0, 24), 1),
                "worksheet_leave_days": round(random.uniform(0, 24), 1),
                "updated_at": f"2026-05-{random.randint(10, 28)}T12:00",
            }
        )

    audit_events = [
        {
            "audit_id": "AUD-EMP118-LEAVE-04",
            "case_id": "CASE-118",
            "employee_id": "EMP-118",
            "timestamp": "2026-04-04T10:00",
            "actor": "QA Bot",
            "event": "leave.profile_mismatch",
            "source": "Audit Service",
            "detail": "QA result: profile_summary_stale. Approved assignment LA-118-APP-02 controls leave policy.",
        },
        {
            "audit_id": "AUD-PAY122-07",
            "case_id": "CASE-122",
            "employee_id": "EMP-122",
            "timestamp": "2026-04-08T10:00",
            "actor": "Payroll QA",
            "event": "payroll.ready",
            "source": "Audit Service",
            "detail": "QA result: ready_with_monitoring. Submitted salary assignment PAY-122-SUB-03 matches accrual batch ACCR-2026-04-B.",
        },
        {
            "audit_id": "AUD-CASE221-09",
            "case_id": "CASE-RW-221",
            "employee_id": "EMP-221",
            "timestamp": "2026-04-24T10:00",
            "actor": "Legal QA",
            "event": "notice.defect",
            "source": "Audit Service",
            "detail": "Formal notice missing appeal instructions; return notice for reissue before close.",
        },
        {
            "audit_id": "AUD-CASE445-03",
            "case_id": "CASE-445",
            "employee_id": "EMP-255",
            "timestamp": "2026-05-13T10:00",
            "actor": "People Ops QA",
            "event": "case.close_blocked",
            "source": "Audit Service",
            "detail": "QA result: block close. Folder lacks executive-exception-approval.pdf and benefits-election.pdf; notice lacks appeal instructions and acknowledgement deadline.",
        },
        {
            "audit_id": "AUD-PAY255-02",
            "case_id": "CASE-445",
            "employee_id": "EMP-255",
            "timestamp": "2026-05-13T11:00",
            "actor": "Payroll QA",
            "event": "payroll.draft_excluded",
            "source": "Audit Service",
            "detail": "Submitted PAY-255-SUB-02 controls; draft PAY-255-DRAFT-03 must be ignored for current payroll.",
        },
        {
            "audit_id": "AUD-REQOPS-11",
            "case_id": "REQ-OPS-19",
            "employee_id": "CAND-OPS-1901",
            "timestamp": "2026-05-15T11:00",
            "actor": "Recruiting QA",
            "event": "notice.defect",
            "source": "Audit Service",
            "detail": "Waitlisted candidate CAND-OPS-1901 notice omits waitlist status; payroll handoff waits for accepted candidate assignment.",
        },
        {
            "audit_id": "AUD-DOC118-06",
            "case_id": "CASE-118",
            "employee_id": "EMP-118",
            "timestamp": "2026-04-06T09:00",
            "actor": "Records QA",
            "event": "folder.tag_missing",
            "source": "Audit Service",
            "detail": "Folder DOC-PRIYA-POL is not ready: decision-record.txt is absent and required tag PolicyException2026 is missing.",
        },
        {
            "audit_id": "AUD-XMODULE-77",
            "case_id": "XMODULE-77",
            "employee_id": "multiple",
            "timestamp": "2026-05-15T15:00",
            "actor": "People Ops Control Tower",
            "event": "cross_module.escalation_package",
            "source": "Audit Service",
            "detail": "Package opened for combined lifecycle risk. Related events: AUD-CASE445-03, AUD-PAY255-02, AUD-REQOPS-11. Review each related event before assigning entity-level issues. Control owner: People Ops Compliance. Remediation clock: 5 business days.",
        },
    ]

    attachments_445 = [
        {
            "attachment_id": "ATT-445-REQUEST",
            "name": "request-summary.txt",
            "kind": "Text",
            "status": "Filed",
            "uploaded_by": "People Ops",
            "uploaded_at": "2026-05-10T12:00",
            "content": "Request summary for CASE-445 and EMP-255 Erin Novak.",
        },
        {
            "attachment_id": "ATT-445-FOLDER",
            "name": "folder-checklist.txt",
            "kind": "Checklist",
            "status": "Missing required evidence",
            "uploaded_by": "Records",
            "uploaded_at": "2026-05-12T12:00",
            "content": "Folder DOC-ERIN-ONB missing benefits-election.pdf and executive-exception-approval.pdf. Required tag PolicyException2026 is missing.",
        },
    ]
    cases = [
        case(
            "CASE-RW-221",
            "Remote-work exception review for Rahul Johnson",
            "EMP-221",
            "Rahul Johnson",
            "Remote work exception",
            "In Review",
            "High",
            "Legal Desk",
            "Approved with conditions but notice must be reissued.",
            [
                {
                    "approval_id": "APP-221-FINAL",
                    "approver": "HR Director",
                    "decision": "Approved",
                    "decided_at": "2026-04-22T12:00",
                    "note": "Approved with conditions.",
                    "step": "Final approval",
                }
            ],
            [
                {
                    "attachment_id": "ATT-221-FOLDER",
                    "name": "folder-checklist.txt",
                    "kind": "Checklist",
                    "status": "Missing tax equalization",
                    "uploaded_by": "Records",
                    "uploaded_at": "2026-04-23T12:00",
                    "content": "Missing tax-equalization-agreement.pdf. Tag PolicyException2026 present.",
                }
            ],
            [audit_events[2]],
            [
                {
                    "comment_id": "CMT-221-1",
                    "author": "Legal Desk",
                    "created_at": "2026-04-23T12:00",
                    "visibility": "Internal",
                    "body": "Formal notice lacks appeal instructions.",
                }
            ],
            ["HR-POL-014", "POL-DOCS-2026"],
        ),
        case(
            "CASE-445",
            "Remote-work exception and lifecycle hold for Erin Novak",
            "EMP-255",
            "Erin Novak",
            "Remote work exception",
            "In Review",
            "High",
            "People Ops Compliance",
            "Approval is final; closeout readiness must be verified from approvals, folder checklist, notice review, and audit detail.",
            [
                {
                    "approval_id": "APP-445-INTAKE",
                    "approver": "People Ops",
                    "decision": "Approved",
                    "decided_at": "2026-05-10T12:00",
                    "note": "Intake complete.",
                    "step": "Intake",
                },
                {
                    "approval_id": "APP-445-FINAL",
                    "approver": "VP People",
                    "decision": "Approved",
                    "decided_at": "2026-05-12T12:00",
                    "note": "Approved with conditions.",
                    "step": "Final approval",
                },
            ],
            attachments_445,
            [audit_events[3], audit_events[4]],
            [
                {
                    "comment_id": "CMT-445-1",
                    "author": "People Ops Compliance",
                    "created_at": "2026-05-13T12:00",
                    "visibility": "Internal",
                    "body": "Hold closeout until executive approval, benefits election, and corrected formal notice are filed.",
                }
            ],
            ["HR-POL-014", "LEAVE-SRC-001", "PAY-SRC-001", "POL-DOCS-2026"],
        ),
        case(
            "REQ-DA-77",
            "Data Analyst recruitment reconciliation",
            "REQ-DA-77",
            "Data Analyst candidates",
            "Recruiting pipeline",
            "Submitted",
            "Medium",
            "Recruiting Desk",
            "Recruitment packet submitted; use candidate review, offer register, ledger, messages, and policy gate before routing follow-up.",
            [],
            [],
            [],
            [],
            ["PAY-SRC-001"],
        ),
        case(
            "REQ-OPS-19",
            "People Operations Analyst recruitment reconciliation",
            "REQ-OPS-19",
            "People Ops candidates",
            "Recruiting pipeline",
            "Submitted",
            "High",
            "Recruiting Desk",
            "Recruitment packet submitted; use candidate review, offer register, ledger, messages, and audit detail before routing follow-up.",
            [],
            [],
            [audit_events[5]],
            [],
            ["PAY-SRC-001"],
        ),
        case(
            "CASE-118",
            "Leave summary correction for Nadia Brooks",
            "EMP-118",
            "Nadia Brooks",
            "Leave policy setup",
            "Needs Info",
            "Medium",
            "People Ops",
            "Profile summary is stale; approved assignment controls.",
            [],
            [
                {
                    "attachment_id": "ATT-118-DOC",
                    "name": "folder-checklist.txt",
                    "kind": "Checklist",
                    "status": "Missing decision record",
                    "uploaded_by": "Records",
                    "uploaded_at": "2026-04-05T12:00",
                    "content": "Folder DOC-PRIYA-POL missing decision-record.txt and tag PolicyException2026.",
                }
            ],
            [audit_events[0], audit_events[6]],
            [],
            ["LEAVE-SRC-001", "POL-DOCS-2026"],
        ),
        case(
            "CASE-122",
            "Payroll assignment readiness for Omar Patel",
            "EMP-122",
            "Omar Patel",
            "Salary structure change",
            "Approved",
            "Medium",
            "Payroll",
            "Submitted assignment is ready with monitoring.",
            [],
            [],
            [audit_events[1]],
            [],
            ["PAY-SRC-001"],
        ),
        case(
            "XMODULE-77",
            "Cross-module lifecycle control package",
            "multiple",
            "Multiple records",
            "Document correction",
            "Submitted",
            "Urgent",
            "People Ops Compliance",
            "Escalation package opened; inspect related audit events before assigning issue owners and SLA.",
            [],
            [],
            [audit_events[7], audit_events[3], audit_events[4], audit_events[5]],
            [],
            ["LEAVE-SRC-001", "PAY-SRC-001", "POL-DOCS-2026"],
        ),
    ]

    recruitment = [
        {
            "opening_id": "REQ-DA-77",
            "title": "Data Analyst",
            "status": "Submitted",
            "cost_ledger": [
                {"line_id": "REQ-DA-77-COST-01", "label": "Agency sourcing invoice", "amount": 4800},
                {"line_id": "REQ-DA-77-COST-02", "label": "Background screening batch", "amount": 900},
                {"line_id": "REQ-DA-77-COST-03", "label": "Interview scheduling platform chargeback", "amount": 500},
            ],
            "candidates": [
                {
                    "candidate_id": "CAND-DA-7701",
                    "name": "Mira Shah",
                    "pipeline_stage": "Final committee",
                    "committee_decision": "Selected",
                    "notice_status": "Offer package approved",
                    "rounds": [5, 5],
                },
                {
                    "candidate_id": "CAND-DA-7702",
                    "name": "Owen Parker",
                    "pipeline_stage": "Final committee",
                    "committee_decision": "Waitlisted",
                    "notice_status": "Notice not sent",
                    "rounds": [4, 4],
                },
                {
                    "candidate_id": "CAND-DA-7703",
                    "name": "Leah Kim",
                    "pipeline_stage": "Final committee",
                    "committee_decision": "Rejected",
                    "notice_status": "Notice not sent",
                    "rounds": [2],
                },
            ],
            "offer_register": [
                {
                    "offer_id": "OFFER-DA-7701",
                    "candidate_id": "CAND-DA-7701",
                    "status": "accepted",
                    "base_salary": 112000,
                }
            ],
            "payroll_precheck_records": [],
            "notice_packets": [
                {
                    "candidate_id": "CAND-DA-7702",
                    "notice_type": "waitlist",
                    "status": "not_sent",
                    "required_action": "send_waitlist_notice",
                },
                {
                    "candidate_id": "CAND-DA-7703",
                    "notice_type": "rejection",
                    "status": "not_sent",
                    "required_action": "send_rejection_notice",
                },
            ],
        },
        {
            "opening_id": "REQ-OPS-19",
            "title": "Operations Coordinator",
            "status": "Submitted",
            "cost_ledger": [
                {"line_id": "REQ-OPS-19-COST-01", "label": "Agency sourcing invoice", "amount": 3000},
                {"line_id": "REQ-OPS-19-COST-02", "label": "Interview panel coordination", "amount": 1850},
                {"line_id": "REQ-OPS-19-COST-03", "label": "Background screening batch", "amount": 1250},
                {"line_id": "REQ-OPS-19-COST-04", "label": "Candidate travel reimbursement", "amount": 750},
                {"line_id": "REQ-OPS-19-COST-05", "label": "Job board renewal allocation", "amount": 500},
            ],
            "candidates": [
                {
                    "candidate_id": "CAND-OPS-1901",
                    "name": "Elena Brooks",
                    "pipeline_stage": "Final committee",
                    "committee_decision": "Waitlisted",
                    "notice_status": "Sent; quality review flagged",
                    "rounds": [4, 4],
                },
                {
                    "candidate_id": "CAND-OPS-1902",
                    "name": "Tomas Reed",
                    "pipeline_stage": "Final committee",
                    "committee_decision": "Selected",
                    "notice_status": "Offer package approved",
                    "rounds": [5, 5],
                },
                {
                    "candidate_id": "CAND-OPS-1903",
                    "name": "Noor Patel",
                    "pipeline_stage": "Final committee",
                    "committee_decision": "Rejected",
                    "notice_status": "Rejection notice sent",
                    "rounds": [3],
                },
                {
                    "candidate_id": "CAND-OPS-1904",
                    "name": "Jonah Mills",
                    "pipeline_stage": "Final committee",
                    "committee_decision": "Rejected",
                    "notice_status": "Rejection notice sent",
                    "rounds": [2],
                },
            ],
            "offer_register": [
                {
                    "offer_id": "OFFER-OPS-1902",
                    "candidate_id": "CAND-OPS-1902",
                    "status": "accepted",
                    "base_salary": 124000,
                }
            ],
            "payroll_precheck_records": [
                {
                    "candidate_id": "CAND-OPS-1901",
                    "record_id": "PAY-PRECHECK-OPS-1901-D",
                    "status": "Draft",
                    "note": "Draft waitlist placeholder; not a submitted assignment.",
                }
            ],
            "notice_packets": [
                {
                    "candidate_id": "CAND-OPS-1901",
                    "message_id": "MSG-OPS-WAITLIST",
                    "notice_type": "waitlist",
                    "status": "draft_reissue_required",
                    "quality": "defective",
                    "defects": ["missing_waitlist_status"],
                    "required_action": "reissue_waitlist_notice_not_rejection",
                }
            ],
            "audit_event_id": "AUD-REQOPS-11",
        },
    ]
    messages = [
        {
            "message_id": "MSG-RW-221",
            "case_id": "CASE-RW-221",
            "channel": "Email",
            "recipient": "Rahul Johnson",
            "sent_at": "2026-04-24T12:00",
            "status": "Draft",
            "subject": "Formal Decision CASE-RW-221",
            "quality": "defective",
            "defects": ["missing_appeal_instructions"],
            "body": "Approved with conditions. Acknowledgement requested by 2026-04-25.",
        },
        {
            "message_id": "MSG-ERIN-445",
            "case_id": "CASE-445",
            "channel": "Email",
            "recipient": "Erin Novak",
            "sent_at": "2026-05-13T12:00",
            "status": "Draft",
            "subject": "Formal Decision CASE-445",
            "quality": "defective",
            "defects": ["missing_ack_deadline", "missing_appeal_instructions"],
            "body": "Approved with conditions. Appeal section and acknowledgement deadline are missing.",
        },
        {
            "message_id": "MSG-PRIYA-118",
            "case_id": "CASE-118",
            "channel": "HRMS inbox",
            "recipient": "Nadia Brooks",
            "sent_at": "2026-04-05T12:00",
            "status": "Draft",
            "subject": "Leave Summary Correction EMP-118",
            "quality": "defective",
            "defects": ["missing_correct_policy"],
            "body": "References legacy profile policy rather than approved assignment.",
        },
        {
            "message_id": "MSG-OPS-WAITLIST",
            "case_id": "REQ-OPS-19",
            "channel": "Email",
            "recipient": "CAND-OPS-1901",
            "sent_at": "2026-05-15T12:00",
            "status": "Draft",
            "subject": "OPS Analyst waitlist follow-up",
            "quality": "defective",
            "defects": ["missing_waitlist_status"],
            "body": "Waitlist status is omitted.",
        },
    ]

    write("employees.json", employees)
    write("departments.json", departments)
    write("policies.json", policies)
    write("cases.json", cases)
    write("payroll_ledgers.json", payroll_ledgers)
    write("recruitment.json", recruitment)
    write("documents.json", documents)
    write("messages.json", messages)
    write("notifications.json", messages)
    write("audit_events.json", audit_events)
    write(
        "manifest.json",
        {
            "seed": SEED,
            "generated_at": "2026-06-05T00:00:00Z",
            "entry_points": {
                "web": "<TASK_ENV_BASE_URL>/",
                "api_summary": "/api/summary",
                "api_cases": "/api/cases",
            },
            "business_modules": [
                "Dashboard",
                "Employees",
                "Recruitment",
                "Leave",
                "Payroll",
                "Policy Cases",
                "Documents",
                "Messages",
                "Audit Log",
            ],
            "files": {
                "employees.json": len(employees),
                "cases.json": len(cases),
                "payroll_ledgers.json": len(payroll_ledgers),
                "recruitment.json": len(recruitment),
                "documents.json": len(documents),
                "messages.json": len(messages),
                "audit_events.json": len(audit_events),
                "policies.json": len(policies),
            },
        },
    )


if __name__ == "__main__":
    main()
