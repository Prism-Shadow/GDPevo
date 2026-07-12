#!/usr/bin/env python3
"""Generate deterministic shared legal-investigation fixture data."""

from __future__ import annotations

import json
import random
from pathlib import Path


SEED = 17017
GENERATION_TIMESTAMP = "2026-07-07T00:00:00Z"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "generated"
MANIFEST_PATH = BASE_DIR / "manifest.json"

ENDPOINTS = [
    "/health",
    "/api/matters",
    "/api/matters/{matter_id}",
    "/api/subpoena_categories?matter_id=...",
    "/api/production_logs?matter_id=...",
    "/api/collection_events?matter_id=...",
    "/api/retention_rules?matter_id=...",
    "/api/destruction_events?matter_id=...",
    "/api/privilege_logs?matter_id=...",
    "/api/qc_events?matter_id=...",
    "/api/custodians?matter_id=...",
    "/api/documents?matter_id=...",
    "/api/search?matter_id=...&q=...",
]

TARGET_COUNTS = {
    "matters": 12,
    "custodians": 72,
    "subpoena_categories": 144,
    "production_logs": 360,
    "collection_events": 190,
    "retention_rules": 72,
    "destruction_events": 96,
    "privilege_logs": 252,
    "qc_events": 180,
    "documents": 720,
}


MATTERS = [
    {
        "matter_id": "M-CRN-041",
        "name": "Crownpoint Neurodevices Market Integrity Inquiry",
        "investigation_type": "white-collar defense / market manipulation",
        "agency": "SEC Enforcement Division",
        "subpoena_date": "2024-03-14",
        "hold_date": "2024-03-15",
        "production_protocol_flag": True,
        "deadline": "2024-08-30",
        "issue_status": "active production review",
        "regulator_notice_flag": True,
        "summary": (
            "Subpoena seeks market-manipulation communications, board materials, "
            "complaints, legal-hold and internal-investigation records, and "
            "personal devices."
        ),
    },
    {
        "matter_id": "M-NVK-219",
        "name": "Novakem Environmental Grand Jury Subpoena",
        "investigation_type": "grand jury environmental",
        "agency": "DOJ Environmental Crimes Section",
        "subpoena_date": "2024-11-22",
        "hold_date": "2024-11-25",
        "production_protocol_flag": True,
        "deadline": "2025-03-14",
        "issue_status": "active production review",
        "regulator_notice_flag": True,
        "summary": (
            "Grand jury subpoena covers lab data, communications, audit reports, "
            "equipment records, former employees, and personal devices."
        ),
    },
    {
        "matter_id": "M-GCF-088",
        "name": "Granite Crest Fund Advisory Fee Investigation",
        "investigation_type": "investment-adviser disclosure",
        "agency": "SEC Asset Management Unit",
        "subpoena_date": "2024-07-08",
        "hold_date": "2024-07-09",
        "production_protocol_flag": True,
        "deadline": "2024-12-06",
        "issue_status": "active production review",
        "regulator_notice_flag": False,
        "summary": (
            "Advisory-fee matter covering custodian device records, shared-drive "
            "materials, personal-email references, privilege-review records, and "
            "attachment-processing records."
        ),
    },
    {
        "matter_id": "M-RDL-304",
        "name": "Radialon Compliance Whistleblower Production",
        "investigation_type": "whistleblower retaliation and compliance",
        "agency": "Department of Labor OIG",
        "subpoena_date": "2024-05-10",
        "hold_date": "2024-05-13",
        "production_protocol_flag": True,
        "deadline": "2024-09-20",
        "issue_status": "active production review",
        "regulator_notice_flag": True,
        "summary": (
            "Whistleblower production review covering complaint documents, "
            "compliance communications, privilege-review records, and review "
            "coding records."
        ),
    },
    {
        "matter_id": "M-PHN-612",
        "name": "Phaneron Health Network Compliance Subpoena",
        "investigation_type": "healthcare compliance",
        "agency": "HHS OIG",
        "subpoena_date": "2024-09-03",
        "hold_date": "2024-09-05",
        "production_protocol_flag": False,
        "deadline": "2025-01-16",
        "issue_status": "active production review",
        "regulator_notice_flag": False,
        "summary": (
            "Former compliance-custodian subpoena covering personnel records, "
            "email archives, Teams records, returned-laptop materials, and "
            "personal cloud/text source inventories."
        ),
    },
    {
        "matter_id": "M-ALD-507",
        "name": "Alderline Revenue Recognition Inquiry",
        "investigation_type": "revenue-recognition accounting",
        "agency": "SEC Financial Reporting and Audit Group",
        "subpoena_date": "2024-08-12",
        "hold_date": "2024-08-14",
        "production_protocol_flag": True,
        "deadline": "2024-12-18",
        "issue_status": "active production review",
        "regulator_notice_flag": True,
        "summary": (
            "Revenue-recognition subpoena covering accounting, board materials, "
            "custodian communications, and privilege-review records across "
            "multiple review systems."
        ),
    },
    {
        "matter_id": "M-BAY-144",
        "name": "Bay & Tidewater Emissions Data Matter",
        "investigation_type": "environmental emissions",
        "agency": "EPA Criminal Investigation Division",
        "subpoena_date": "2024-12-04",
        "hold_date": "2024-12-06",
        "production_protocol_flag": True,
        "deadline": "2025-04-15",
        "issue_status": "active production review",
        "regulator_notice_flag": True,
        "summary": (
            "Environmental subpoena covering lab records, collaboration systems, "
            "executive email archives, vendor audit materials, and custodian "
            "source inventories."
        ),
    },
    {
        "matter_id": "M-LYN-322",
        "name": "Lynxion Consulting Payments Investigation",
        "investigation_type": "books and records / consulting payments",
        "agency": "DOJ Fraud Section",
        "subpoena_date": "2024-08-20",
        "hold_date": "2024-08-22",
        "production_protocol_flag": True,
        "deadline": "2025-01-24",
        "issue_status": "active production review",
        "regulator_notice_flag": True,
        "summary": (
            "Consulting-payments investigation centered on custodian C-MR-118, "
            "reviewing device, shared-folder, personal-email, privilege, and "
            "attachment-processing records."
        ),
    },
    {
        "matter_id": "M-OVL-730",
        "name": "Overlook Integrated Production Readiness Review",
        "investigation_type": "multi-issue integrated production",
        "agency": "SEC and DOJ Joint Task Force",
        "subpoena_date": "2025-01-08",
        "hold_date": "2025-01-09",
        "production_protocol_flag": True,
        "deadline": "2025-05-02",
        "issue_status": "active production review",
        "regulator_notice_flag": False,
        "summary": (
            "Integrated production review with categories O-01 through O-10 across "
            "communications, board, archive, review-platform, attachment, "
            "shared-folder, accounting, vendor, and regulator record sources."
        ),
    },
    {
        "matter_id": "M-KTR-556",
        "name": "Kestrel Therapeutics Speaker Program Review",
        "investigation_type": "healthcare anti-kickback",
        "agency": "DOJ Civil Division",
        "subpoena_date": "2024-02-02",
        "hold_date": "2024-02-05",
        "production_protocol_flag": True,
        "deadline": "2024-07-12",
        "issue_status": "active production review",
        "regulator_notice_flag": False,
        "summary": "Noisy comparator matter with overlapping custodian aliases and stale coding notes.",
    },
    {
        "matter_id": "M-SIL-902",
        "name": "Silvergate Meridian Trading Surveillance Inquiry",
        "investigation_type": "trading surveillance",
        "agency": "CFTC Division of Enforcement",
        "subpoena_date": "2024-10-21",
        "hold_date": "2024-10-22",
        "production_protocol_flag": False,
        "deadline": "2025-03-06",
        "issue_status": "active production review",
        "regulator_notice_flag": False,
        "summary": "Noisy comparator with similar market-communications categories and obsolete policies.",
    },
    {
        "matter_id": "M-TVL-689",
        "name": "TruVale Procurement Controls Inquiry",
        "investigation_type": "procurement fraud",
        "agency": "State Attorney General",
        "subpoena_date": "2024-06-17",
        "hold_date": "2024-06-19",
        "production_protocol_flag": True,
        "deadline": "2024-11-05",
        "issue_status": "active production review",
        "regulator_notice_flag": False,
        "summary": "Noisy comparator matter with overlapping tags and unrelated privilege rows.",
    },
]

MATTER_IDS = [matter["matter_id"] for matter in MATTERS]


BASE_CATEGORIES = {
    "M-CRN-041": [
        (
            "CRN-01",
            "Market-manipulation communications",
            "2022-01-01",
            "2024-03-14",
            ["email", "Teams", "Bloomberg chat"],
            ["market manipulation", "trading", "communications"],
        ),
        (
            "CRN-02",
            "Board materials concerning trading strategy",
            "2021-07-01",
            "2024-03-14",
            ["board portal", "shared drive"],
            ["board materials", "strategy"],
        ),
        (
            "CRN-03",
            "Complaints and testing-accuracy concerns",
            "2021-01-01",
            "2024-03-14",
            ["email", "hotline", "QA shared drive"],
            ["complaints", "testing accuracy"],
        ),
        (
            "CRN-04",
            "Legal hold and internal investigation records",
            "2024-03-01",
            "2024-06-30",
            ["legal hold system", "email"],
            ["legal hold", "internal investigation"],
        ),
        (
            "CRN-05",
            "Personal devices and encrypted messaging",
            "2022-01-01",
            "2024-03-14",
            ["personal phone", "Signal", "WhatsApp"],
            ["personal devices", "messaging"],
        ),
        (
            "CRN-06",
            "Counsel communications about trading inquiry",
            "2023-09-01",
            "2024-03-14",
            ["email", "legal files"],
            ["counsel communications", "privilege"],
        ),
    ],
    "M-NVK-219": [
        (
            "N-01",
            "Environmental lab data and raw test results",
            "2019-01-01",
            "2024-11-22",
            ["LIMS", "off-site boxes"],
            ["lab data", "emissions"],
        ),
        (
            "N-02",
            "Environmental communications",
            "2020-01-01",
            "2024-11-22",
            ["email", "Teams", "voicemail"],
            ["communications", "environment"],
        ),
        (
            "N-03",
            "Audit reports and draft findings",
            "2019-01-01",
            "2024-11-22",
            ["shared drive", "vendor portal"],
            ["audit report", "retention"],
        ),
        (
            "N-04",
            "Equipment calibration and maintenance records",
            "2019-01-01",
            "2024-11-22",
            ["maintenance database"],
            ["equipment", "calibration"],
        ),
        (
            "N-05",
            "Former employee custodial materials",
            "2019-01-01",
            "2024-11-22",
            ["email archive", "off-site storage"],
            ["former employees"],
        ),
        (
            "N-06",
            "Personal devices used for EHS communications",
            "2020-01-01",
            "2024-11-22",
            ["personal phone", "SMS"],
            ["personal devices"],
        ),
    ],
    "M-GCF-088": [
        (
            "G-01",
            "Advisory fee communications",
            "2022-01-01",
            "2024-07-08",
            ["email", "Teams"],
            ["fees", "communications"],
        ),
        (
            "G-02",
            "Board and investor materials",
            "2022-01-01",
            "2024-07-08",
            ["board portal", "shared drive"],
            ["investors", "board"],
        ),
        (
            "G-03",
            "Shared-drive working files",
            "2022-01-01",
            "2024-07-08",
            ["shared drive"],
            ["shared drive", "deletions"],
        ),
        (
            "G-04",
            "Personal email and external forwards",
            "2022-01-01",
            "2024-07-08",
            ["Gmail", "email"],
            ["personal email", "external forwards"],
        ),
        (
            "G-05",
            "Privilege and clawback review",
            "2024-07-01",
            "2024-11-30",
            ["review platform"],
            ["privilege", "clawback"],
        ),
        (
            "G-06",
            "Attachments and encrypted files",
            "2022-01-01",
            "2024-07-08",
            ["email attachments"],
            ["attachments", "QC"],
        ),
    ],
    "M-RDL-304": [
        (
            "R-01",
            "Whistleblower complaints and compliance escalations",
            "2021-01-01",
            "2024-05-10",
            ["email", "hotline"],
            ["whistleblower", "complaints"],
        ),
        (
            "R-02",
            "Compliance committee materials",
            "2021-01-01",
            "2024-05-10",
            ["shared drive"],
            ["compliance", "committee"],
        ),
        ("R-03", "Internal audit workpapers", "2021-01-01", "2024-05-10", ["audit share"], ["audit", "workpapers"]),
        ("R-04", "Manager communications", "2021-01-01", "2024-05-10", ["email", "Teams"], ["communications"]),
        (
            "R-10",
            "Privilege review and coding quality",
            "2024-05-01",
            "2024-09-20",
            ["review platform"],
            ["privilege", "QC"],
        ),
        (
            "R-11",
            "Counsel communications on compliance response",
            "2023-01-01",
            "2024-05-10",
            ["email", "legal files"],
            ["counsel communications", "privilege"],
        ),
    ],
    "M-PHN-612": [
        (
            "P-01",
            "Former compliance custodian personnel file",
            "2020-01-01",
            "2024-09-03",
            ["HRIS", "personnel file"],
            ["personnel", "former custodian"],
        ),
        (
            "P-02",
            "Compliance email including Iron archive",
            "2019-01-01",
            "2024-09-03",
            ["active mailbox", "Iron archive"],
            ["email archive"],
        ),
        ("P-03", "Teams compliance chats", "2020-01-01", "2024-09-03", ["Teams"], ["Teams", "purge"]),
        ("P-04", "Returned laptop and local PST", "2020-01-01", "2024-09-03", ["laptop", "PST"], ["laptop", "PST"]),
        (
            "P-05",
            "Personal cloud and text messaging",
            "2020-01-01",
            "2024-09-03",
            ["iCloud", "SMS"],
            ["personal cloud", "texts"],
        ),
    ],
    "M-ALD-507": [
        (
            "A-01",
            "Revenue-recognition communications",
            "2021-01-01",
            "2024-08-12",
            ["email", "Teams"],
            ["revenue recognition", "communications"],
        ),
        (
            "A-02",
            "Board packages and finance committee materials",
            "2021-01-01",
            "2024-08-12",
            ["board portal", "shared drive"],
            ["board package"],
        ),
        (
            "A-03",
            "Journal-entry override support",
            "2021-01-01",
            "2024-08-12",
            ["ERP", "shared drive"],
            ["journal entries", "override"],
        ),
        (
            "A-04",
            "Personal messages for finance executives",
            "2021-01-01",
            "2024-08-12",
            ["personal phone", "Signal", "Telegram"],
            ["personal messages"],
        ),
        (
            "A-08",
            "Prior counsel logistics",
            "2022-01-01",
            "2024-08-12",
            ["email", "legal files"],
            ["counsel logistics", "privilege"],
        ),
        (
            "A-09",
            "Complaints about revenue-recognition overrides",
            "2021-01-01",
            "2024-08-12",
            ["email", "hotline"],
            ["complaints", "override"],
        ),
    ],
    "M-BAY-144": [
        (
            "B-01",
            "Emissions lab data and raw results",
            "2020-01-01",
            "2024-12-04",
            ["LIMS", "off-site boxes"],
            ["lab data", "emissions"],
        ),
        (
            "B-02",
            "Teams channels and EHS discussions",
            "2021-01-01",
            "2024-12-04",
            ["Teams"],
            ["Teams", "channel records"],
        ),
        (
            "B-03",
            "Executive email and VaultSeven archive",
            "2021-01-01",
            "2024-12-04",
            ["active mailbox", "VaultSeven archive"],
            ["executive email", "archive"],
        ),
        (
            "B-04",
            "Tidewater audit reports",
            "2021-01-01",
            "2024-12-04",
            ["vendor portal", "shared drive"],
            ["audit report", "vendor copy"],
        ),
        (
            "B-05",
            "Off-site vendor boxes and personal devices",
            "2021-01-01",
            "2024-12-04",
            ["off-site storage", "personal phone"],
            ["vendor boxes", "personal devices"],
        ),
    ],
    "M-LYN-322": [
        (
            "L-01",
            "Consulting payment approvals",
            "2021-01-01",
            "2024-08-20",
            ["email", "ERP"],
            ["consulting payments"],
        ),
        (
            "L-02",
            "M. Rivas laptop and local files",
            "2021-01-01",
            "2024-08-20",
            ["work laptop"],
            ["laptop", "local files"],
        ),
        (
            "L-03",
            "Shared-folder payment files",
            "2021-01-01",
            "2024-08-20",
            ["shared folder"],
            ["shared folder", "file recovery"],
        ),
        ("L-04", "Personal Outlook references", "2021-01-01", "2024-08-20", ["personal Outlook"], ["personal email"]),
        (
            "L-05",
            "Consultant communications and forwards",
            "2021-01-01",
            "2024-08-20",
            ["email"],
            ["consultant", "external forwards"],
        ),
        (
            "L-06",
            "Privilege coding and attachments",
            "2024-08-01",
            "2025-01-24",
            ["review platform", "attachments"],
            ["privilege", "attachments"],
        ),
    ],
    "M-OVL-730": [
        (
            "O-01",
            "Executive communications",
            "2023-01-01",
            "2025-01-08",
            ["email", "Teams"],
            ["executive", "communications"],
        ),
        (
            "O-02",
            "Board minutes and presentations",
            "2023-01-01",
            "2025-01-08",
            ["board portal"],
            ["board", "presentations"],
        ),
        (
            "O-03",
            "Phone and chat messages",
            "2023-01-01",
            "2025-01-08",
            ["personal phone", "Signal"],
            ["phone", "chat"],
        ),
        ("O-04", "Legacy archive mail", "2022-01-01", "2025-01-08", ["mail archive"], ["archive", "mail export"]),
        (
            "O-05",
            "Privilege review universe",
            "2024-01-01",
            "2025-01-08",
            ["review platform"],
            ["privilege", "review platform"],
        ),
        (
            "O-06",
            "Encrypted attachments",
            "2023-01-01",
            "2025-01-08",
            ["email attachments"],
            ["attachments", "processing"],
        ),
        (
            "O-07",
            "Shared-folder deleted files",
            "2023-01-01",
            "2025-01-08",
            ["shared folder"],
            ["shared folder", "file recovery"],
        ),
        ("O-08", "Accounting exports", "2023-01-01", "2025-01-08", ["ERP"], ["accounting", "exports"]),
        (
            "O-09",
            "Vendor communications",
            "2023-01-01",
            "2025-01-08",
            ["vendor portal", "email"],
            ["vendor", "communications"],
        ),
        (
            "O-10",
            "Regulator correspondence",
            "2023-01-01",
            "2025-01-08",
            ["email", "matter files"],
            ["regulator", "correspondence"],
        ),
    ],
}

NOISE_CATEGORY_LABELS = [
    "Expense approval emails",
    "Calendar invites and logistics",
    "Training acknowledgments",
    "Draft policy revisions",
    "Sales forecast workpapers",
    "Vendor onboarding files",
    "Pricing committee notes",
    "Data-room exports",
    "Compliance certifications",
    "Obsolete retention-policy references",
    "Duplicate custodian aliases",
    "Regional operations chat",
    "Archive exception reports",
    "Invoice exception escalations",
    "Document-review guide notes",
]

SOURCE_TYPES = [
    "email",
    "Teams",
    "Slack",
    "shared drive",
    "board portal",
    "personal phone",
    "archive mailbox",
    "review platform",
    "off-site box",
    "laptop",
    "vendor portal",
]

ROLES = [
    "Chief Financial Officer",
    "General Counsel",
    "Compliance Manager",
    "Controller",
    "QA Director",
    "Plant Manager",
    "Investor Relations Lead",
    "EHS Specialist",
    "Procurement Director",
    "Former Regional VP",
    "Legal Operations Manager",
    "Board Secretary",
]

FIRST_NAMES = [
    "Avery",
    "Blake",
    "Casey",
    "Devon",
    "Elliot",
    "Finley",
    "Greer",
    "Harper",
    "Indra",
    "Jordan",
    "Kai",
    "Logan",
    "Morgan",
    "Nico",
    "Parker",
    "Quinn",
    "Riley",
    "Sasha",
    "Taylor",
    "Vera",
]

LAST_NAMES = [
    "Aldrin",
    "Bennett",
    "Chen",
    "Diaz",
    "Elliott",
    "Farrow",
    "Grant",
    "Hale",
    "Ibarra",
    "Jensen",
    "Kapoor",
    "Lee",
    "Mori",
    "Nash",
    "Ortiz",
    "Patel",
    "Quade",
    "Rivas",
    "Stone",
    "Tan",
]


def dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compact_id(prefix: str, number: int) -> str:
    return f"{prefix}-{number:03d}"


def add_category(
    categories: list[dict],
    matter_id: str,
    category_id: str,
    label: str,
    start_date: str,
    end_date: str,
    requested_sources: list[str],
    topic_tags: list[str],
) -> None:
    categories.append(
        {
            "matter_id": matter_id,
            "category_id": category_id,
            "label": label,
            "date_range": {"start": start_date, "end": end_date},
            "requested_sources": requested_sources,
            "topic_tags": topic_tags,
        }
    )


def build_categories(rng: random.Random) -> list[dict]:
    categories: list[dict] = []
    for matter_id, rows in BASE_CATEGORIES.items():
        for row in rows:
            add_category(categories, matter_id, *row)

    counters = dict.fromkeys(MATTER_IDS, 1)
    while len(categories) < TARGET_COUNTS["subpoena_categories"]:
        matter_id = rng.choice(MATTER_IDS)
        prefix = matter_id.split("-")[1][:2]
        category_id = f"{prefix}-N{counters[matter_id]:03d}"
        counters[matter_id] += 1
        if any(row["matter_id"] == matter_id and row["category_id"] == category_id for row in categories):
            continue
        label = rng.choice(NOISE_CATEGORY_LABELS)
        add_category(
            categories,
            matter_id,
            category_id,
            label,
            f"{rng.choice([2019, 2020, 2021, 2022, 2023])}-01-01",
            rng.choice(["2024-03-31", "2024-08-31", "2024-12-31", "2025-02-28"]),
            rng.sample(SOURCE_TYPES, k=rng.randint(1, 3)),
            rng.sample(
                [
                    "communications",
                    "logistics",
                    "review coding",
                    "archive",
                    "privilege",
                    "retention",
                    "obsolete policy",
                    "duplicate alias",
                    "vendor",
                    "board",
                    "complaints",
                ],
                k=rng.randint(2, 4),
            ),
        )
    return categories


def build_custodians(rng: random.Random) -> list[dict]:
    fixed = [
        (
            "C-GW-014",
            "M-CRN-041",
            "G. Weller",
            "Trading Strategy VP",
            "active",
            ["email", "personal phone", "Signal", "WhatsApp"],
            ["personal phone factory reset six days after subpoena; Signal and WhatsApp unavailable"],
        ),
        (
            "C-QA-027",
            "M-CRN-041",
            "R. Sen",
            "Former QA Director",
            "former",
            ["email", "QA shared drive"],
            ["testing-accuracy concern email miscoded non-responsive"],
        ),
        (
            "C-LB-048",
            "M-NVK-219",
            "L. Barrow",
            "Lab Records Manager",
            "former",
            ["LIMS", "off-site boxes"],
            ["2019 lab data boxes destroyed before hold"],
        ),
        (
            "C-EH-052",
            "M-NVK-219",
            "E. Horne",
            "EHS Director",
            "active",
            ["email", "Teams", "voicemail"],
            ["Teams before February 2022 likely lost; voicemail overwritten after 90 days"],
        ),
        (
            "C-HL-033",
            "M-GCF-088",
            "H. Lang",
            "Portfolio Operations Lead",
            "active",
            ["work laptop", "shared drive", "Gmail", "email"],
            ["old laptop wiped after hold; personal Gmail uncollected"],
        ),
        (
            "C-RW-066",
            "M-RDL-304",
            "N. Rowe",
            "Compliance Hotline Manager",
            "active",
            ["email", "hotline"],
            ["complaint documents miscoded outside broad category"],
        ),
        (
            "C-FC-072",
            "M-PHN-612",
            "F. Chao",
            "Former Compliance Custodian",
            "former",
            ["personnel file", "Iron archive", "Teams", "laptop", "PST"],
            ["separated in 2022; local PST missing from returned laptop"],
        ),
        (
            "C-TP-090",
            "M-ALD-507",
            "T. Price",
            "Revenue Controller",
            "active",
            ["phone", "Signal", "Telegram", "email"],
            ["phone encrypted and not collected after subpoena; Signal and Telegram unavailable"],
        ),
        (
            "C-DI-091",
            "M-ALD-507",
            "D. Ibarra",
            "Senior Revenue Accountant",
            "active",
            ["email", "ERP"],
            ["complaint about revenue-recognition override miscoded non-responsive"],
        ),
        (
            "C-VS-104",
            "M-BAY-144",
            "V. Singh",
            "Emissions Lab Manager",
            "active",
            ["LIMS", "Teams", "off-site boxes"],
            ["2020 lab data destroyed pre-hold; Teams channels purged post-hold"],
        ),
        (
            "C-MR-118",
            "M-LYN-322",
            "M. Rivas",
            "Consulting Payments Director",
            "active",
            ["laptop", "shared folder", "personal Outlook", "email"],
            ["laptop wiped after hold; personal Outlook uncollected"],
        ),
        (
            "C-OV-201",
            "M-OVL-730",
            "J. Ovid",
            "Integrated Review Lead",
            "active",
            ["email", "board portal", "phone", "archive", "review platform"],
            ["integrated review coordinator"],
        ),
    ]
    custodians = [
        {
            "custodian_id": cid,
            "matter_id": matter_id,
            "name": name,
            "role": role,
            "status": status,
            "relevant_sources": sources,
            "known_gaps": gaps,
        }
        for cid, matter_id, name, role, status, sources, gaps in fixed
    ]
    for matter_id in MATTER_IDS:
        if any(row["matter_id"] == matter_id for row in custodians):
            continue
        prefix = matter_id.split("-")[1][:2]
        custodians.append(
            {
                "custodian_id": f"C-{prefix}-000",
                "matter_id": matter_id,
                "name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                "role": rng.choice(ROLES),
                "status": rng.choice(["active", "former"]),
                "relevant_sources": rng.sample(SOURCE_TYPES, k=3),
                "known_gaps": ["noisy comparator custodian with overlapping aliases"],
            }
        )
    i = 1
    while len(custodians) < TARGET_COUNTS["custodians"]:
        matter_id = MATTER_IDS[(len(custodians) + i) % len(MATTER_IDS)]
        custodian_id = compact_id(f"C-{matter_id.split('-')[1][:2]}", i)
        i += 1
        if any(row["custodian_id"] == custodian_id for row in custodians):
            continue
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        sources = rng.sample(SOURCE_TYPES, k=rng.randint(2, 5))
        gap = rng.choice(
            [
                "none noted",
                "duplicate alias appears in review platform",
                "stale review-guide coding from prior subpoena",
                "archive mailbox requires validation",
                "mobile source not in initial hold notice",
                "obsolete retention label in collection memo",
            ]
        )
        custodians.append(
            {
                "custodian_id": custodian_id,
                "matter_id": matter_id,
                "name": name,
                "role": rng.choice(ROLES),
                "status": rng.choice(["active", "former"]),
                "relevant_sources": sources,
                "known_gaps": [gap] if gap != "none noted" else [],
            }
        )
    return custodians


def first_custodian(custodians: list[dict], matter_id: str) -> str:
    for row in custodians:
        if row["matter_id"] == matter_id:
            return row["custodian_id"]
    raise KeyError(matter_id)


def categories_by_matter(categories: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in categories:
        grouped.setdefault(row["matter_id"], []).append(row)
    return grouped


def custodians_by_matter(custodians: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in custodians:
        grouped.setdefault(row["matter_id"], []).append(row)
    return grouped


def build_production_logs(rng: random.Random, categories: list[dict]) -> list[dict]:
    logs: list[dict] = []

    def add(
        matter_id: str,
        category_id: str,
        produced: int,
        withheld: int,
        logged: int,
        status: str,
        notes: str,
        batch: str = "current",
    ) -> None:
        logs.append(
            {
                "log_id": f"PL-{len(logs) + 1:04d}",
                "matter_id": matter_id,
                "category_id": category_id,
                "batch": batch,
                "produced_count": produced,
                "withheld_privileged_count": withheld,
                "privilege_logged_count": logged,
                "review_status": status,
                "notes": notes,
            }
        )

    add(
        "M-CRN-041",
        "CRN-03",
        386,
        74,
        62,
        "needs QC",
        "Former QA director testing-accuracy email collected but miscoded non-responsive under overly narrow complaints category.",
    )
    add(
        "M-CRN-041",
        "CRN-04",
        618,
        4232,
        1847,
        "privilege log incomplete",
        "Privilege-coded records total 4,232; logged total is 1,847, leaving 2,385 unlogged.",
    )
    add(
        "M-CRN-041",
        "CRN-06",
        0,
        1247,
        0,
        "over-designation review",
        "Counsel-communications category has 1,247 withheld and zero produced.",
    )
    add(
        "M-NVK-219", "N-01", 2140, 34, 34, "source gap", "2019 lab data has a four-box pre-hold destruction exception."
    )
    add(
        "M-NVK-219",
        "N-02",
        5510,
        221,
        208,
        "source gap",
        "Voicemail has 90-day overwrite; Teams before February 2022 likely lost.",
    )
    add(
        "M-NVK-219",
        "N-03",
        118,
        17,
        17,
        "batch_record",
        "Missing October 2023 environmental audit report should still exist under five-year retention.",
    )
    add(
        "M-GCF-088",
        "G-04",
        233,
        67,
        59,
        "waiver review",
        "Three privileged emails were forwarded to outside banker; personal Gmail not collected.",
    )
    add(
        "M-GCF-088",
        "G-05",
        1190,
        413,
        376,
        "clawback review",
        "12 business-only emails over-designated; 45 privileged documents initially coded non-privileged.",
    )
    add(
        "M-GCF-088",
        "G-06",
        482,
        25,
        25,
        "current_batch_record",
        "Attachment processing records show 14 password-protected and 9 corrupt items.",
    )
    add(
        "M-RDL-304",
        "R-01",
        0,
        88,
        71,
        "batch_record",
        "Zero produced for broad whistleblower/compliance category even though two complaint documents exist and were miscoded.",
    )
    add(
        "M-RDL-304",
        "R-10",
        1440,
        2910,
        2102,
        "privilege log incomplete",
        "Withheld privileged total 2,910; logged total 2,102; unlogged gap 808.",
    )
    add(
        "M-RDL-304",
        "R-11",
        0,
        612,
        0,
        "over-designation review",
        "Counsel communications category has all 612 responsive records withheld.",
    )
    add(
        "M-PHN-612",
        "P-01",
        94,
        6,
        6,
        "current_batch_record",
        "Former compliance custodian personnel-file dates appear in retention records.",
    )
    add(
        "M-PHN-612",
        "P-02",
        2012,
        156,
        148,
        "archive validation",
        "Iron archive contains older email despite active mailbox purge.",
    )
    add("M-PHN-612", "P-03", 775, 41, 41, "source gap", "Teams default purge created pre-2022 gap.")
    add("M-PHN-612", "P-04", 30, 2, 2, "source gap", "Laptop return record indicates missing local PST.")
    add(
        "M-PHN-612",
        "P-05",
        0,
        0,
        0,
        "hold supplement needed",
        "Hold notice omitted personal cloud and text messaging.",
    )
    add(
        "M-ALD-507",
        "A-04",
        0,
        0,
        0,
        "current_batch_record",
        "Current batch has no collected records for the listed mobile messaging sources.",
    )
    add(
        "M-ALD-507",
        "A-09",
        228,
        36,
        31,
        "current_batch_record",
        "One complaint marker has conflicting review coding in QC records.",
    )
    add(
        "M-ALD-507",
        "A-02",
        142,
        11,
        11,
        "current_batch_record",
        "Board package marker is tracked in a separate portal record.",
    )
    add(
        "M-ALD-507",
        "A-08",
        0,
        980,
        0,
        "current_batch_record",
        "Current row has withheld records and no produced records for the counsel logistics category.",
    )
    add(
        "M-ALD-507",
        "A-01",
        3295,
        3640,
        2275,
        "current_batch_record",
        "Privileged-coded and logged count fields differ for the current production row.",
    )
    add(
        "M-BAY-144",
        "B-01",
        1824,
        19,
        19,
        "current_batch_record",
        "Lab-data source has a retention note in the source-event records.",
    )
    add(
        "M-BAY-144",
        "B-02",
        910,
        56,
        56,
        "current_batch_record",
        "Teams source has an event record dated 2025-02-05/2025-02-06.",
    )
    add(
        "M-BAY-144",
        "B-03",
        2338,
        109,
        109,
        "current_batch_record",
        "Executive email archive has a separate archive-source record.",
    )
    add(
        "M-BAY-144",
        "B-04",
        87,
        4,
        4,
        "current_batch_record",
        "Tidewater audit material appears in retention and vendor-source records.",
    )
    add(
        "M-BAY-144",
        "B-05",
        0,
        0,
        0,
        "current_batch_record",
        "Hold-scope records list off-site vendor boxes and personal devices.",
    )
    add(
        "M-LYN-322",
        "L-02",
        314,
        22,
        20,
        "current_batch_record",
        "Laptop source has a collection-event record dated 2024-09-18.",
    )
    add(
        "M-LYN-322",
        "L-03",
        770,
        44,
        44,
        "current_batch_record",
        "Shared-folder recovery counts are recorded in QC events.",
    )
    add(
        "M-LYN-322",
        "L-04",
        0,
        0,
        0,
        "current_batch_record",
        "Personal Outlook source appears in collection-event records.",
    )
    add(
        "M-LYN-322",
        "L-05",
        536,
        108,
        96,
        "current_batch_record",
        "Consultant-forward records are tracked in privilege-log records.",
    )
    add(
        "M-LYN-322",
        "L-06",
        883,
        317,
        290,
        "current_batch_record",
        "Privilege review and attachment-processing counts are recorded in QC and privilege-log records.",
    )
    ovl_rows = [
        ("O-01", 820, 28, 28, "current_batch_record", "Current batch count loaded from review platform."),
        ("O-02", 116, 5, 5, "current_batch_record", "Current batch count loaded from review platform."),
        (
            "O-03",
            0,
            0,
            0,
            "current_batch_record",
            "Phone and chat source counts should be reconciled with collection events.",
        ),
        (
            "O-04",
            0,
            0,
            0,
            "current_batch_record",
            "Archive-source counts should be reconciled with collection events.",
        ),
        (
            "O-05",
            450,
            520,
            310,
            "current_batch_record",
            "Privilege withheld and logged count fields differ for this row.",
        ),
        (
            "O-06",
            390,
            18,
            18,
            "current_batch_record",
            "Attachment-processing records should be reconciled with QC events.",
        ),
        (
            "O-07",
            278,
            9,
            9,
            "current_batch_record",
            "Shared-folder counts should be reconciled with source-event records.",
        ),
        ("O-08", 690, 12, 12, "current_batch_record", "Current batch count loaded from review platform."),
        ("O-09", 344, 8, 8, "current_batch_record", "Current batch count loaded from review platform."),
        ("O-10", 73, 21, 21, "current_batch_record", "Current batch count loaded from review platform."),
    ]
    for category_id, produced, withheld, logged, status, notes in ovl_rows:
        add("M-OVL-730", category_id, produced, withheld, logged, status, notes)

    grouped = categories_by_matter(categories)
    while len(logs) < TARGET_COUNTS["production_logs"]:
        matter_id = rng.choice(MATTER_IDS)
        category = rng.choice(grouped[matter_id])
        withheld = rng.randint(0, 180)
        logged = max(0, withheld - rng.randint(0, min(withheld, 35)))
        produced = rng.randint(0, 1800)
        status = rng.choice(
            [
                "batch_record",
                "in_review",
                "source_reconciliation",
                "review_reconciliation",
                "coding_reconciliation",
                "archive_reconciliation",
                "partial_batch_record",
            ]
        )
        note = rng.choice(
            [
                "Includes stale review coding from an earlier subpoena wave.",
                "Internal review-guide label is narrower than subpoena category scope.",
                "Collection exception may override production tracker completeness.",
                "Duplicate custodian alias caused overlapping family counts.",
                "Unrelated privilege entries remain in the same review batch.",
                "Obsolete retention policy cited in source memo; current rule stored separately.",
            ]
        )
        add(
            matter_id,
            category["category_id"],
            produced,
            withheld,
            logged,
            status,
            note,
            batch=f"noise-{len(logs) % 7 + 1}",
        )
    return logs


def build_retention_rules(rng: random.Random) -> list[dict]:
    rules: list[dict] = []

    def add(matter_id: str, record_class: str, period: str, trigger: str, archive_override: str, notes: str) -> None:
        rules.append(
            {
                "rule_id": f"RR-{len(rules) + 1:04d}",
                "matter_id": matter_id,
                "record_class": record_class,
                "retention_period": period,
                "trigger": trigger,
                "archive_override": archive_override,
                "notes": notes,
            }
        )

    add(
        "M-NVK-219",
        "2019 lab data boxes",
        "3 years",
        "calendar year close",
        "none",
        "Four 2019 lab-data boxes destroyed in January 2023 before the 2024 hold.",
    )
    add(
        "M-NVK-219",
        "EHS correspondence boxes",
        "5 years",
        "matter close",
        "legal hold suspends destruction",
        "Vendor destroyed two EHS correspondence boxes on January 6, 2025 after hold.",
    )
    add(
        "M-NVK-219",
        "voicemail",
        "90 days",
        "message date",
        "none",
        "Voicemail overwritten after 90 days absent export.",
    )
    add(
        "M-NVK-219",
        "Teams chat",
        "standard tenant purge",
        "message date",
        "none",
        "Teams before February 2022 likely lost.",
    )
    add(
        "M-NVK-219",
        "executive email archive",
        "7 years",
        "message date",
        "email archive overrides active-server purge",
        "Archive retains seven years despite active-server purge.",
    )
    add(
        "M-NVK-219",
        "environmental audit reports",
        "5 years",
        "report final date",
        "vendor copy required",
        "October 2023 environmental audit should still exist.",
    )
    add(
        "M-PHN-612",
        "personnel file",
        "5 years after separation",
        "separation date",
        "HR archive",
        "Former compliance custodian separated in 2022; personnel file should exist through 2027.",
    )
    add(
        "M-PHN-612",
        "email",
        "7 years",
        "message date",
        "Iron archive overrides active mailbox purge",
        "Iron archive contains older email despite mailbox purge.",
    )
    add(
        "M-PHN-612",
        "Teams chat",
        "tenant default purge",
        "message date",
        "none",
        "Teams default purge created pre-2022 gap.",
    )
    add(
        "M-PHN-612",
        "local PST",
        "until device return processing",
        "return date",
        "none",
        "Laptop return record indicates missing local PST.",
    )
    add(
        "M-BAY-144",
        "2020 emissions lab data",
        "3 years",
        "calendar year close",
        "none",
        "Source record lists destruction under the three-year rule before the matter hold date.",
    )
    add(
        "M-BAY-144",
        "Teams channel content",
        "litigation hold suspended",
        "hold date",
        "none",
        "Source record lists 11 unavailable Teams channels with a 2025-02-05 event date.",
    )
    add(
        "M-BAY-144",
        "executive email",
        "7 years",
        "message date",
        "VaultSeven archive overrides active purge",
        "VaultSeven retains executive email.",
    )
    add(
        "M-BAY-144",
        "Tidewater audit report",
        "5 years",
        "report final date",
        "vendor copy required",
        "2024 audit report should exist under retention and vendor copy.",
    )
    add(
        "M-ALD-507",
        "board packages",
        "7 years",
        "meeting date",
        "board portal copy",
        "Missing Q2 2022 board package exists in separate board portal.",
    )
    add(
        "M-ALD-507",
        "personal messages",
        "legal hold required",
        "hold date",
        "none",
        "Hold and collection gap for C-TP-090 encrypted phone.",
    )

    record_classes = [
        "email",
        "chat",
        "board materials",
        "audit reports",
        "expense records",
        "device images",
        "vendor boxes",
        "hotline complaints",
        "calibration logs",
        "policy acknowledgments",
    ]
    while len(rules) < TARGET_COUNTS["retention_rules"]:
        matter_id = rng.choice(MATTER_IDS)
        period = rng.choice(["90 days", "1 year", "3 years", "5 years", "7 years", "until matter close"])
        add(
            matter_id,
            rng.choice(record_classes),
            period,
            rng.choice(
                ["message date", "calendar year close", "employee separation", "report final date", "hold date"]
            ),
            rng.choice(
                [
                    "none",
                    "archive copy",
                    "vendor copy",
                    "legal hold suspends destruction",
                    "obsolete policy superseded",
                ]
            ),
            rng.choice(
                [
                    "Current rule conflicts with an obsolete policy name in one collection note.",
                    "Archive availability should be checked before treating purge as final loss.",
                    "Retention timing is evaluated against hold date and subpoena lookback.",
                    "No exception noted in current policy table.",
                ]
            ),
        )
    return rules


def build_destruction_events(rng: random.Random) -> list[dict]:
    events: list[dict] = []

    def add(
        matter_id: str,
        record_class: str,
        event_date: str,
        quantity: int,
        timing: str,
        policy_basis: str,
        recoverability: str,
        category_ids: list[str],
    ) -> None:
        events.append(
            {
                "event_id": f"DE-{len(events) + 1:04d}",
                "matter_id": matter_id,
                "record_class": record_class,
                "event_date": event_date,
                "quantity": quantity,
                "pre_or_post_hold": timing,
                "policy_basis": policy_basis,
                "recoverability": recoverability,
                "related_category_ids": category_ids,
            }
        )

    add(
        "M-CRN-041",
        "C-GW-014 personal phone",
        "2024-03-20",
        1,
        "post-hold",
        "factory reset six days after subpoena",
        "Signal and WhatsApp unavailable; no usable device image",
        ["CRN-05"],
    )
    add(
        "M-NVK-219",
        "2019 lab data boxes",
        "2023-01-18",
        4,
        "pre-hold",
        "three-year retention rule",
        "not recoverable from boxes; lab summaries partly available",
        ["N-01"],
    )
    add(
        "M-NVK-219",
        "EHS correspondence boxes",
        "2025-01-06",
        2,
        "post-hold",
        "vendor destruction despite hold",
        "vendor index only; originals unavailable",
        ["N-02", "N-05"],
    )
    add(
        "M-GCF-088",
        "C-HL-033 old laptop",
        "2024-08-02",
        1,
        "post-hold",
        "work laptop replaced after hold and old laptop wiped",
        "not recoverable from device image",
        ["G-02", "G-03"],
    )
    add(
        "M-GCF-088",
        "shared-drive files",
        "2024-08-10",
        37,
        "post-hold",
        "manual folder deletion",
        "29 recovered; 8 unrecovered",
        ["G-03"],
    )
    add(
        "M-LYN-322",
        "C-MR-118 laptop",
        "2024-09-18",
        1,
        "post-hold",
        "device refresh wipe after hold",
        "not recoverable from laptop image",
        ["L-02"],
    )
    add(
        "M-LYN-322",
        "shared-folder files",
        "2024-09-24",
        52,
        "post-hold",
        "shared-folder deletion after hold",
        "41 recovered; 11 unrecovered",
        ["L-03"],
    )
    add(
        "M-BAY-144",
        "2020 emissions lab data",
        "2023-01-27",
        6,
        "pre-hold",
        "three-year retention rule",
        "summary exports only; destruction before hold",
        ["B-01"],
    )
    add(
        "M-BAY-144",
        "Teams channels",
        "2025-02-05",
        11,
        "post-hold",
        "automated channel-retention job",
        "channel metadata only; message bodies unavailable",
        ["B-02"],
    )
    add(
        "M-OVL-730",
        "shared-folder deleted files",
        "2025-02-14",
        19,
        "post-hold",
        "automated cleanup after hold",
        "partial recovery pending",
        ["O-07"],
    )

    while len(events) < TARGET_COUNTS["destruction_events"]:
        matter_id = rng.choice(MATTER_IDS)
        add(
            matter_id,
            rng.choice(
                [
                    "email archive shard",
                    "chat export",
                    "device image",
                    "off-site box",
                    "shared folder",
                    "voicemail",
                    "old policy binder",
                ]
            ),
            f"{rng.choice([2022, 2023, 2024, 2025])}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            rng.randint(1, 80),
            rng.choice(["pre-hold", "post-hold", "unclear"]),
            rng.choice(
                [
                    "standard purge",
                    "obsolete retention policy",
                    "vendor cleanup",
                    "manual deletion",
                    "device replacement",
                ]
            ),
            rng.choice(
                [
                    "recoverable from archive",
                    "partially recoverable",
                    "not recoverable",
                    "metadata only",
                    "duplicate copy exists",
                ]
            ),
            [f"{matter_id.split('-')[1][:2]}-N{rng.randint(1, 40):03d}"],
        )
    return events


def build_privilege_logs(rng: random.Random, custodians: list[dict], categories: list[dict]) -> list[dict]:
    logs: list[dict] = []

    def add(
        matter_id: str,
        category_id: str,
        custodian_id: str,
        privilege_status: str,
        logged_status: str,
        waiver_risk: bool,
        overdesignation: bool,
        production_status: str,
        record_count: int,
        notes: str,
    ) -> None:
        logs.append(
            {
                "item_id": f"PV-{len(logs) + 1:04d}",
                "matter_id": matter_id,
                "category_id": category_id,
                "custodian_id": custodian_id,
                "privilege_status": privilege_status,
                "logged_status": logged_status,
                "waiver_risk": waiver_risk,
                "overdesignation_flag": overdesignation,
                "production_status": production_status,
                "record_count": record_count,
                "notes": notes,
            }
        )

    add(
        "M-CRN-041",
        "CRN-04",
        "C-GW-014",
        "privileged-coded",
        "partially logged",
        False,
        False,
        "withheld",
        4232,
        "Privilege-coded records 4,232; 1,847 logged; 2,385 unlogged.",
    )
    add(
        "M-CRN-041",
        "CRN-06",
        "C-GW-014",
        "counsel communications",
        "not logged",
        False,
        True,
        "withheld",
        1247,
        "Counsel-communications category has zero produced and over-designation risk.",
    )
    add(
        "M-GCF-088",
        "G-04",
        "C-HL-033",
        "privileged forwarded externally",
        "logged",
        True,
        False,
        "withheld",
        3,
        "Three privileged emails forwarded to outside banker.",
    )
    add(
        "M-GCF-088",
        "G-05",
        "C-HL-033",
        "business-only",
        "not logged",
        False,
        True,
        "withheld",
        12,
        "Business-only emails over-designated as privileged.",
    )
    add(
        "M-GCF-088",
        "G-05",
        "C-HL-033",
        "privileged investigation",
        "not logged",
        False,
        False,
        "produced",
        45,
        "Privileged documents initially coded non-privileged; clawback risk.",
    )
    add(
        "M-RDL-304",
        "R-10",
        "C-RW-066",
        "privileged-coded",
        "partially logged",
        False,
        False,
        "withheld",
        2910,
        "Withheld privileged total 2,910; logged 2,102; unlogged 808.",
    )
    add(
        "M-RDL-304",
        "R-11",
        "C-RW-066",
        "counsel communications",
        "not logged",
        False,
        True,
        "withheld",
        612,
        "All responsive records withheld in counsel communications category.",
    )
    add(
        "M-ALD-507",
        "A-01",
        "C-TP-090",
        "privileged-coded",
        "partially logged",
        False,
        False,
        "withheld",
        3640,
        "Privileged-coded records 3,640; logged 2,275; unlogged 1,365.",
    )
    add(
        "M-ALD-507",
        "A-08",
        "C-TP-090",
        "prior counsel logistics",
        "not logged",
        False,
        True,
        "withheld",
        980,
        "Prior counsel logistics category has zero produced and over-designation risk.",
    )
    add(
        "M-LYN-322",
        "L-05",
        "C-MR-118",
        "legal-advice forwarded externally",
        "logged",
        True,
        False,
        "withheld",
        4,
        "Four legal-advice emails forwarded to consultant K. Sato.",
    )
    add(
        "M-LYN-322",
        "L-06",
        "C-MR-118",
        "business-only scheduling/logistics",
        "not logged",
        False,
        True,
        "withheld",
        18,
        "Business-only scheduling/logistics emails over-designated.",
    )
    add(
        "M-LYN-322",
        "L-06",
        "C-MR-118",
        "privileged investigation",
        "not logged",
        False,
        False,
        "produced",
        39,
        "Privileged investigation emails first-pass coded non-privileged.",
    )
    add(
        "M-OVL-730",
        "O-05",
        "C-OV-201",
        "privileged-coded",
        "partially logged",
        False,
        False,
        "withheld",
        520,
        "Privilege withheld and logged count fields differ for O-05.",
    )

    grouped_custodians = custodians_by_matter(custodians)
    grouped_categories = categories_by_matter(categories)
    while len(logs) < TARGET_COUNTS["privilege_logs"]:
        matter_id = rng.choice(MATTER_IDS)
        custodian_id = rng.choice(grouped_custodians[matter_id])["custodian_id"]
        category_id = rng.choice(grouped_categories[matter_id])["category_id"]
        status = rng.choice(
            ["privileged-coded", "not privileged", "work product", "business-only", "counsel communications"]
        )
        production_status = rng.choice(["produced", "withheld", "redacted", "needs review"])
        overdesignation = (
            status in {"business-only", "counsel communications"}
            and production_status == "withheld"
            and rng.random() < 0.35
        )
        add(
            matter_id,
            category_id,
            custodian_id,
            status,
            rng.choice(["logged", "not logged", "partially logged", "not required"]),
            rng.random() < 0.08,
            overdesignation,
            production_status,
            rng.randint(1, 140),
            rng.choice(
                [
                    "Unrelated privilege row from overlapping review batch.",
                    "Review note references stale privilege taxonomy.",
                    "Forwarded thread requires waiver analysis.",
                    "Business-only logistics thread may be over-designated.",
                    "Logged count should be compared to withheld privilege total.",
                ]
            ),
        )
    return logs


def build_qc_events(rng: random.Random) -> list[dict]:
    events: list[dict] = []

    def add(
        matter_id: str,
        custodian_id: str,
        issue_type: str,
        affected: int,
        recovered: int,
        failed: int,
        related_docs: list[str],
        hint: str,
    ) -> None:
        events.append(
            {
                "event_id": f"QC-{len(events) + 1:04d}",
                "matter_id": matter_id,
                "custodian_id": custodian_id,
                "issue_type": issue_type,
                "affected_count": affected,
                "recovered_count": recovered,
                "failed_count": failed,
                "related_document_ids": related_docs,
                "review_note": hint,
            }
        )

    add(
        "M-CRN-041",
        "C-QA-027",
        "miscoded complaint",
        1,
        1,
        0,
        ["DOC-CRN-TEST-ACC-001"],
        "Compare complaint marker records with the subpoena category scope.",
    )
    add(
        "M-GCF-088",
        "C-HL-033",
        "shared-drive deletion recovery",
        37,
        29,
        8,
        ["DOC-GCF-SHARED-001", "DOC-GCF-SHARED-008"],
        "Collection/QC event overrides tracker completeness.",
    )
    add(
        "M-GCF-088",
        "C-HL-033",
        "privilege miscoding",
        45,
        0,
        45,
        ["DOC-GCF-PRIV-001", "DOC-GCF-PRIV-045"],
        "Compare privilege coding fields against production status for these documents.",
    )
    add(
        "M-GCF-088",
        "C-HL-033",
        "attachment processing",
        23,
        0,
        23,
        ["DOC-GCF-ATT-014", "DOC-GCF-ATT-023"],
        "Attachment processing records show 14 password-protected and 9 corrupt items.",
    )
    add(
        "M-RDL-304",
        "C-RW-066",
        "miscoded complaint documents",
        2,
        2,
        0,
        ["DOC-RDL-COMP-001", "DOC-RDL-COMP-002"],
        "Complaint documents belong in broad whistleblower/compliance category.",
    )
    add(
        "M-RDL-304",
        "C-RW-066",
        "privileged coded non-privileged",
        31,
        0,
        31,
        ["DOC-RDL-PRIV-001", "DOC-RDL-PRIV-031"],
        "Compare privilege coding fields against production status for these documents.",
    )
    add(
        "M-ALD-507",
        "C-DI-091",
        "miscoded complaint",
        1,
        1,
        0,
        ["DOC-ALD-IBARRA-001"],
        "D. Ibarra complaint marker has a category-scope review note.",
    )
    add(
        "M-ALD-507",
        "C-TP-090",
        "missing board package",
        1,
        1,
        0,
        ["DOC-ALD-BOARD-Q2-2022"],
        "Separate board portal contains the Q2 2022 board package marker.",
    )
    add(
        "M-LYN-322",
        "C-MR-118",
        "shared-folder deletion recovery",
        52,
        41,
        11,
        ["DOC-LYN-SHARED-001", "DOC-LYN-SHARED-052"],
        "Shared-folder recovery record shows affected, recovered, and failed counts.",
    )
    add(
        "M-LYN-322",
        "C-MR-118",
        "privileged coded non-privileged",
        39,
        0,
        39,
        ["DOC-LYN-PRIV-001", "DOC-LYN-PRIV-039"],
        "Privilege coding fields should be compared against production status.",
    )
    add(
        "M-LYN-322",
        "C-MR-118",
        "attachment processing",
        31,
        0,
        31,
        ["DOC-LYN-ATT-017", "DOC-LYN-ATT-031"],
        "Attachment processing records show 17 password-protected and 14 corrupt items.",
    )
    add(
        "M-OVL-730",
        "C-OV-201",
        "attachment processing",
        16,
        0,
        16,
        ["DOC-OVL-ATT-001", "DOC-OVL-ATT-016"],
        "Attachment processing records are associated with O-06.",
    )
    add(
        "M-OVL-730",
        "C-OV-201",
        "shared-folder recovery",
        19,
        7,
        12,
        ["DOC-OVL-DEL-001", "DOC-OVL-DEL-019"],
        "Shared-folder deletion/recovery records are associated with O-07.",
    )

    issue_types = [
        "stale review coding",
        "duplicate family suppression",
        "archive validation",
        "privilege overlay mismatch",
        "missing attachment text",
        "duplicate custodian alias",
        "source exception reconciliation",
    ]
    while len(events) < TARGET_COUNTS["qc_events"]:
        matter_id = rng.choice(MATTER_IDS)
        affected = rng.randint(1, 90)
        recovered = rng.randint(0, affected)
        failed = affected - recovered
        add(
            matter_id,
            f"C-{matter_id.split('-')[1][:2]}-{rng.randint(1, 60):03d}",
            rng.choice(issue_types),
            affected,
            recovered,
            failed,
            [f"DOC-{matter_id.split('-')[1]}-{rng.randint(1, 720):04d}"],
            rng.choice(
                [
                    "Confirm whether collection/QC notes override production tracker.",
                    "Resolve stale coding before marking category complete.",
                    "Check archive availability before final loss conclusion.",
                    "Compare review guide to subpoena category scope.",
                ]
            ),
        )
    return events


def build_collection_events(rng: random.Random, custodians: list[dict], categories: list[dict]) -> list[dict]:
    events: list[dict] = []

    def add(
        matter_id: str,
        custodian_id: str,
        source_type: str,
        source_name: str,
        status: str,
        event_date: str,
        hold_relation: str,
        collected: int,
        missing: int,
        reason: str,
        category_ids: list[str],
    ) -> None:
        events.append(
            {
                "event_id": f"CE-{len(events) + 1:04d}",
                "matter_id": matter_id,
                "custodian_id": custodian_id,
                "source_type": source_type,
                "source_name": source_name,
                "status": status,
                "event_date": event_date,
                "hold_relation": hold_relation,
                "collected_count": collected,
                "missing_count": missing,
                "reason": reason,
                "related_category_ids": category_ids,
            }
        )

    add(
        "M-CRN-041",
        "C-GW-014",
        "personal phone",
        "G. Weller iPhone",
        "unavailable",
        "2024-03-21",
        "post-hold",
        0,
        1,
        "Factory reset six days after subpoena; Signal and WhatsApp unavailable.",
        ["CRN-05"],
    )
    add(
        "M-CRN-041",
        "C-QA-027",
        "email",
        "R. Sen former QA mailbox",
        "collected",
        "2024-04-02",
        "post-hold",
        1240,
        0,
        "Testing-accuracy concern email collected but miscoded non-responsive.",
        ["CRN-03"],
    )
    add(
        "M-NVK-219",
        "C-LB-048",
        "off-site boxes",
        "2019 lab data four boxes",
        "destroyed before hold",
        "2025-01-10",
        "pre-hold destruction identified",
        0,
        4,
        "Destroyed in January 2023 under three-year retention rule.",
        ["N-01"],
    )
    add(
        "M-NVK-219",
        "C-EH-052",
        "off-site boxes",
        "Vendor EHS correspondence boxes",
        "destroyed after hold",
        "2025-01-08",
        "post-hold",
        0,
        2,
        "Vendor destroyed boxes on January 6, 2025 after hold.",
        ["N-02", "N-05"],
    )
    add(
        "M-NVK-219",
        "C-EH-052",
        "Teams",
        "EHS Teams tenant",
        "partial",
        "2024-12-12",
        "post-hold",
        7840,
        1300,
        "Teams before February 2022 likely lost.",
        ["N-02"],
    )
    add(
        "M-NVK-219",
        "C-EH-052",
        "email archive",
        "Seven-year archive",
        "collected",
        "2024-12-14",
        "post-hold",
        11320,
        0,
        "Email archive retains seven years despite active-server purge.",
        ["N-02", "N-05"],
    )
    add(
        "M-NVK-219",
        "C-EH-052",
        "vendor portal",
        "Audit vendor portal",
        "pending",
        "2025-01-20",
        "post-hold",
        87,
        1,
        "Missing October 2023 environmental audit report should still exist under five-year retention.",
        ["N-03"],
    )
    add(
        "M-GCF-088",
        "C-HL-033",
        "work laptop",
        "H. Lang old laptop",
        "wiped",
        "2024-08-02",
        "post-hold",
        0,
        1,
        "Work laptop replaced after hold; old laptop wiped.",
        ["G-02", "G-03"],
    )
    add(
        "M-GCF-088",
        "C-HL-033",
        "shared drive",
        "H. Lang advisory folder",
        "partial",
        "2024-08-11",
        "post-hold",
        29,
        8,
        "37 shared-drive files deleted after hold; 29 recovered and 8 unrecovered.",
        ["G-03"],
    )
    add(
        "M-GCF-088",
        "C-HL-033",
        "personal email",
        "H. Lang Gmail",
        "not collected",
        "2024-08-18",
        "post-hold",
        0,
        1,
        "Personal Gmail uncollected.",
        ["G-04"],
    )
    add(
        "M-PHN-612",
        "C-FC-072",
        "personnel file",
        "F. Chao HR file",
        "available",
        "2024-09-18",
        "post-hold",
        1,
        0,
        "Separated in 2022; personnel file should exist through 2027.",
        ["P-01"],
    )
    add(
        "M-PHN-612",
        "C-FC-072",
        "email archive",
        "Iron archive",
        "collected",
        "2024-09-24",
        "post-hold",
        8320,
        0,
        "Iron archive contains older email despite mailbox purge.",
        ["P-02"],
    )
    add(
        "M-PHN-612",
        "C-FC-072",
        "Teams",
        "F. Chao Teams",
        "partial",
        "2024-09-27",
        "post-hold",
        1440,
        610,
        "Teams default purge created pre-2022 gap.",
        ["P-03"],
    )
    add(
        "M-PHN-612",
        "C-FC-072",
        "laptop",
        "Returned compliance laptop",
        "collected with gap",
        "2024-10-02",
        "post-hold",
        1,
        1,
        "Laptop return record indicates missing local PST.",
        ["P-04"],
    )
    add(
        "M-PHN-612",
        "C-FC-072",
        "personal cloud/text",
        "Personal cloud and text messages",
        "not noticed",
        "2024-10-04",
        "post-hold",
        0,
        2,
        "Hold notice omitted personal cloud and text messaging.",
        ["P-05"],
    )
    add(
        "M-ALD-507",
        "C-TP-090",
        "personal phone",
        "T. Price encrypted phone",
        "not collected",
        "2024-08-24",
        "post-hold",
        0,
        1,
        "Phone encrypted and not collected after subpoena; Signal and Telegram unavailable.",
        ["A-04"],
    )
    add(
        "M-ALD-507",
        "C-DI-091",
        "email",
        "D. Ibarra mailbox",
        "collected",
        "2024-09-01",
        "post-hold",
        2170,
        0,
        "Complaint email about revenue-recognition override collected but coded non-responsive.",
        ["A-09"],
    )
    add(
        "M-ALD-507",
        "C-TP-090",
        "board portal",
        "Finance board portal",
        "found",
        "2024-09-18",
        "post-hold",
        1,
        0,
        "Missing Q2 2022 board package exists in separate board portal.",
        ["A-02"],
    )
    add(
        "M-BAY-144",
        "C-VS-104",
        "off-site boxes",
        "2020 emissions lab data",
        "destroyed before hold",
        "2025-01-09",
        "pre-hold destruction identified",
        0,
        6,
        "Source record lists destruction under the three-year rule before the matter hold date.",
        ["B-01"],
    )
    add(
        "M-BAY-144",
        "C-VS-104",
        "Teams",
        "EHS Teams channels",
        "destroyed after hold",
        "2025-02-06",
        "post-hold",
        0,
        11,
        "Source record lists 11 unavailable Teams channels with a 2025-02-05 event date.",
        ["B-02"],
    )
    add(
        "M-BAY-144",
        "C-VS-104",
        "email archive",
        "VaultSeven executive archive",
        "collected",
        "2025-01-14",
        "post-hold",
        9220,
        0,
        "VaultSeven retains executive email despite active purge.",
        ["B-03"],
    )
    add(
        "M-BAY-144",
        "C-VS-104",
        "vendor portal",
        "Tidewater audit vendor copy",
        "pending",
        "2025-01-22",
        "post-hold",
        0,
        1,
        "Missing 2024 Tidewater audit report should exist under five-year retention and vendor copy.",
        ["B-04"],
    )
    add(
        "M-BAY-144",
        "C-VS-104",
        "off-site vendor boxes",
        "Vendor boxes and personal devices",
        "not noticed",
        "2025-01-28",
        "post-hold",
        0,
        3,
        "Hold notice omitted off-site vendor boxes and personal devices.",
        ["B-05"],
    )
    add(
        "M-LYN-322",
        "C-MR-118",
        "work laptop",
        "M. Rivas laptop",
        "wiped",
        "2024-09-18",
        "post-hold",
        0,
        1,
        "Laptop wiped after hold.",
        ["L-02"],
    )
    add(
        "M-LYN-322",
        "C-MR-118",
        "shared folder",
        "M. Rivas payment shared folder",
        "partial",
        "2024-09-25",
        "post-hold",
        41,
        11,
        "52 shared-folder files deleted; 41 recovered and 11 unrecovered.",
        ["L-03"],
    )
    add(
        "M-LYN-322",
        "C-MR-118",
        "personal email",
        "M. Rivas personal Outlook",
        "not collected",
        "2024-10-01",
        "post-hold",
        0,
        1,
        "Personal Outlook account referenced in produced emails but uncollected.",
        ["L-04"],
    )
    add(
        "M-OVL-730",
        "C-OV-201",
        "phone/chat",
        "Overlook phone and Signal",
        "not collected",
        "2025-02-01",
        "post-hold",
        0,
        2,
        "Phone and chat source is not present in the current collection set.",
        ["O-03"],
    )
    add(
        "M-OVL-730",
        "C-OV-201",
        "mail archive",
        "Legacy archive",
        "missing",
        "2025-02-02",
        "post-hold",
        0,
        1,
        "Archive export is not present in the current collection set.",
        ["O-04"],
    )
    add(
        "M-OVL-730",
        "C-OV-201",
        "shared folder",
        "O-07 shared-folder export",
        "partial",
        "2025-02-15",
        "post-hold",
        7,
        12,
        "Shared-folder source has a dated deletion/recovery event.",
        ["O-07"],
    )

    grouped_custodians = custodians_by_matter(custodians)
    grouped_categories = categories_by_matter(categories)
    while len(events) < TARGET_COUNTS["collection_events"]:
        matter_id = rng.choice(MATTER_IDS)
        custodian = rng.choice(grouped_custodians[matter_id])
        category = rng.choice(grouped_categories[matter_id])
        status = rng.choice(["collected", "partial", "pending", "not collected", "source gap", "archive validation"])
        missing = rng.randint(0, 60) if status != "collected" else 0
        collected = rng.randint(0, 4000)
        add(
            matter_id,
            custodian["custodian_id"],
            rng.choice(SOURCE_TYPES),
            rng.choice(
                [
                    "primary mailbox",
                    "shared folder",
                    "legacy archive",
                    "mobile export",
                    "off-site box",
                    "review upload",
                ]
            ),
            status,
            f"{rng.choice([2024, 2025])}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            rng.choice(["pre-hold", "post-hold", "hold not applicable", "pre-hold destruction identified"]),
            collected,
            missing,
            rng.choice(
                [
                    "Collection note references broader subpoena scope than review-guide coding.",
                    "Archive validation pending before final source status.",
                    "Duplicate custodian alias created overlapping source names.",
                    "Stale review coding may understate responsive material.",
                    "No material exception in current collection log.",
                ]
            ),
            [category["category_id"]],
        )
    return events


def build_documents(rng: random.Random, custodians: list[dict], categories: list[dict]) -> list[dict]:
    docs: list[dict] = []

    def add(
        doc_id: str,
        matter_id: str,
        custodian_id: str,
        category_ids: list[str],
        title: str,
        date: str,
        source_type: str,
        review_coding: str,
        privilege_coding: str,
        production_status: str,
        summary: str,
        tags: list[str],
    ) -> None:
        docs.append(
            {
                "document_id": doc_id,
                "matter_id": matter_id,
                "custodian_id": custodian_id,
                "category_ids": category_ids,
                "title": title,
                "date": date,
                "source_type": source_type,
                "review_coding": review_coding,
                "privilege_coding": privilege_coding,
                "production_status": production_status,
                "summary": summary,
                "tags": tags,
            }
        )

    add(
        "DOC-CRN-TEST-ACC-001",
        "M-CRN-041",
        "C-QA-027",
        ["CRN-03"],
        "Former QA director email re testing accuracy concerns",
        "2023-11-02",
        "email",
        "non-responsive",
        "not privileged",
        "not produced",
        "Email raised testing-accuracy concerns; collected but miscoded under overly narrow complaints category.",
        ["complaint", "testing accuracy", "miscoded"],
    )
    add(
        "DOC-RDL-COMP-001",
        "M-RDL-304",
        "C-RW-066",
        ["R-01"],
        "Hotline complaint on compliance pressure",
        "2023-10-14",
        "email",
        "non-responsive",
        "not privileged",
        "not produced",
        "Complaint document should map to broad whistleblower/compliance category despite miscoding.",
        ["complaint", "whistleblower", "miscoded"],
    )
    add(
        "DOC-RDL-COMP-002",
        "M-RDL-304",
        "C-RW-066",
        ["R-01"],
        "Follow-up compliance escalation complaint",
        "2023-10-18",
        "hotline",
        "non-responsive",
        "not privileged",
        "not produced",
        "Second complaint document exists but production tracker shows zero produced for broad category.",
        ["complaint", "compliance", "miscoded"],
    )
    add(
        "DOC-ALD-IBARRA-001",
        "M-ALD-507",
        "C-DI-091",
        ["A-09"],
        "D. Ibarra revenue-recognition override complaint",
        "2023-12-06",
        "email",
        "non-responsive",
        "not privileged",
        "not produced",
        "D. Ibarra complaint email about revenue-recognition override was collected but coded non-responsive.",
        ["complaint", "revenue recognition", "override", "miscoded"],
    )
    add(
        "DOC-ALD-BOARD-Q2-2022",
        "M-ALD-507",
        "C-TP-090",
        ["A-02"],
        "Q2 2022 board package",
        "2022-07-15",
        "board portal",
        "responsive",
        "not privileged",
        "not produced",
        "Missing board package exists in a separate board portal.",
        ["board package", "Q2 2022", "portal"],
    )
    add(
        "DOC-GCF-PRIV-001",
        "M-GCF-088",
        "C-HL-033",
        ["G-05"],
        "Privileged investigation email first pass 001",
        "2024-07-12",
        "email",
        "responsive",
        "non-privileged",
        "produced",
        "One of 45 privileged documents initially coded non-privileged; clawback risk.",
        ["privilege", "clawback", "miscoded"],
    )
    add(
        "DOC-GCF-PRIV-045",
        "M-GCF-088",
        "C-HL-033",
        ["G-05"],
        "Privileged investigation email first pass 045",
        "2024-07-16",
        "email",
        "responsive",
        "non-privileged",
        "produced",
        "Endpoint marker for 45-document clawback set.",
        ["privilege", "clawback", "miscoded"],
    )
    add(
        "DOC-GCF-SHARED-001",
        "M-GCF-088",
        "C-HL-033",
        ["G-03"],
        "Recovered advisory shared-drive file 001",
        "2024-06-04",
        "shared drive",
        "responsive",
        "not privileged",
        "produced",
        "Recovered from 37 deleted shared-drive files.",
        ["shared drive", "recovered"],
    )
    add(
        "DOC-GCF-SHARED-008",
        "M-GCF-088",
        "C-HL-033",
        ["G-03"],
        "Unrecovered shared-drive file marker 008",
        "2024-06-09",
        "shared drive",
        "unknown",
        "unknown",
        "not produced",
        "Marker for 8 unrecovered shared-drive files.",
        ["shared drive", "unrecovered"],
    )
    add(
        "DOC-GCF-ATT-014",
        "M-GCF-088",
        "C-HL-033",
        ["G-06"],
        "Password-protected attachment batch marker",
        "2024-05-21",
        "attachment",
        "unprocessed",
        "unknown",
        "not produced",
        "14 password-protected attachments failed processing.",
        ["attachment", "password-protected"],
    )
    add(
        "DOC-GCF-ATT-023",
        "M-GCF-088",
        "C-HL-033",
        ["G-06"],
        "Corrupt attachment batch marker",
        "2024-05-22",
        "attachment",
        "unprocessed",
        "unknown",
        "not produced",
        "9 corrupt attachments failed processing.",
        ["attachment", "corrupt"],
    )
    add(
        "DOC-LYN-PRIV-001",
        "M-LYN-322",
        "C-MR-118",
        ["L-06"],
        "Privileged investigation email first pass 001",
        "2024-09-01",
        "email",
        "responsive",
        "non-privileged",
        "produced",
        "One of 39 privileged investigation emails first-pass coded non-privileged.",
        ["privilege", "clawback", "miscoded"],
    )
    add(
        "DOC-LYN-PRIV-039",
        "M-LYN-322",
        "C-MR-118",
        ["L-06"],
        "Privileged investigation email first pass 039",
        "2024-09-04",
        "email",
        "responsive",
        "non-privileged",
        "produced",
        "Endpoint marker for 39 privileged investigation emails miscoded non-privileged.",
        ["privilege", "clawback", "miscoded"],
    )
    add(
        "DOC-LYN-SHARED-001",
        "M-LYN-322",
        "C-MR-118",
        ["L-03"],
        "Recovered payment shared-folder file 001",
        "2024-04-11",
        "shared folder",
        "responsive",
        "not privileged",
        "produced",
        "Recovered from 52 shared-folder deleted files.",
        ["shared folder", "recovered"],
    )
    add(
        "DOC-LYN-SHARED-052",
        "M-LYN-322",
        "C-MR-118",
        ["L-03"],
        "Unrecovered shared-folder file marker 052",
        "2024-04-12",
        "shared folder",
        "unknown",
        "unknown",
        "not produced",
        "Marker for 11 unrecovered shared-folder files.",
        ["shared folder", "unrecovered"],
    )
    add(
        "DOC-LYN-ATT-017",
        "M-LYN-322",
        "C-MR-118",
        ["L-06"],
        "Password-protected attachment marker",
        "2024-07-02",
        "attachment",
        "unprocessed",
        "unknown",
        "not produced",
        "17 password-protected attachments failed processing.",
        ["attachment", "password-protected"],
    )
    add(
        "DOC-LYN-ATT-031",
        "M-LYN-322",
        "C-MR-118",
        ["L-06"],
        "Corrupt attachment marker",
        "2024-07-03",
        "attachment",
        "unprocessed",
        "unknown",
        "not produced",
        "14 corrupt attachments failed processing.",
        ["attachment", "corrupt"],
    )
    add(
        "DOC-RDL-PRIV-001",
        "M-RDL-304",
        "C-RW-066",
        ["R-10"],
        "Privileged compliance advice miscoded 001",
        "2024-05-18",
        "email",
        "responsive",
        "non-privileged",
        "produced",
        "One of 31 privileged records coded non-privileged.",
        ["privilege", "miscoded", "clawback"],
    )
    add(
        "DOC-RDL-PRIV-031",
        "M-RDL-304",
        "C-RW-066",
        ["R-10"],
        "Privileged compliance advice miscoded 031",
        "2024-05-19",
        "email",
        "responsive",
        "non-privileged",
        "produced",
        "Endpoint marker for 31 privileged records coded non-privileged.",
        ["privilege", "miscoded", "clawback"],
    )
    add(
        "DOC-OVL-ATT-001",
        "M-OVL-730",
        "C-OV-201",
        ["O-06"],
        "Overlook encrypted attachment marker 001",
        "2024-11-06",
        "attachment",
        "unprocessed",
        "unknown",
        "not produced",
        "O-06 attachment processing marker.",
        ["O-06", "attachment processing", "batch_record"],
    )
    add(
        "DOC-OVL-ATT-016",
        "M-OVL-730",
        "C-OV-201",
        ["O-06"],
        "Overlook encrypted attachment marker 016",
        "2024-11-08",
        "attachment",
        "unprocessed",
        "unknown",
        "not produced",
        "O-06 attachment processing marker.",
        ["O-06", "attachment processing", "batch_record"],
    )
    add(
        "DOC-OVL-DEL-001",
        "M-OVL-730",
        "C-OV-201",
        ["O-07"],
        "Overlook deleted shared-folder marker 001",
        "2024-12-10",
        "shared folder",
        "responsive",
        "not privileged",
        "not produced",
        "O-07 shared-folder recovery marker.",
        ["O-07", "shared-folder recovery", "batch_record"],
    )
    add(
        "DOC-OVL-DEL-019",
        "M-OVL-730",
        "C-OV-201",
        ["O-07"],
        "Overlook deleted shared-folder marker 019",
        "2024-12-12",
        "shared folder",
        "unknown",
        "unknown",
        "not produced",
        "O-07 shared-folder recovery marker.",
        ["O-07", "shared-folder recovery", "batch_record"],
    )

    grouped_custodians = custodians_by_matter(custodians)
    grouped_categories = categories_by_matter(categories)
    used = {row["document_id"] for row in docs}
    while len(docs) < TARGET_COUNTS["documents"]:
        matter_id = rng.choice(MATTER_IDS)
        custodian_id = rng.choice(grouped_custodians[matter_id])["custodian_id"]
        cats = rng.sample(grouped_categories[matter_id], k=rng.randint(1, min(3, len(grouped_categories[matter_id]))))
        num = len(docs) + 1
        doc_id = f"DOC-{matter_id.split('-')[1]}-{num:04d}"
        if doc_id in used:
            continue
        used.add(doc_id)
        topic = rng.choice(
            [
                "calendar logistics",
                "draft board deck",
                "pricing exception",
                "vendor invoice",
                "archive notice",
                "review coding note",
                "compliance escalation",
                "policy update",
                "duplicate alias memo",
                "privilege overlay report",
            ]
        )
        review = rng.choice(
            ["responsive", "non-responsive", "needs second-level review", "stale coding", "family member"]
        )
        privilege = rng.choice(["not privileged", "privileged", "work product", "unknown", "over-designated"])
        production = rng.choice(["produced", "withheld", "not produced", "redacted", "pending"])
        add(
            doc_id,
            matter_id,
            custodian_id,
            [cat["category_id"] for cat in cats],
            f"{topic.title()} {num:04d}",
            f"{rng.choice([2021, 2022, 2023, 2024])}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            rng.choice(SOURCE_TYPES),
            review,
            privilege,
            production,
            rng.choice(
                [
                    "Noisy document with overlapping tags across subpoena categories.",
                    "Review coding was imported from an older guide and may be stale.",
                    "Document appears in a duplicate custodian alias family.",
                    "Archive source indicates active-system purge is not final loss.",
                    "Business record overlaps with privilege-review batch.",
                ]
            ),
            rng.sample(
                [
                    "communications",
                    "logistics",
                    "archive",
                    "review coding",
                    "privilege",
                    "retention",
                    "vendor",
                    "board",
                    "complaint",
                    "duplicate alias",
                    "obsolete policy",
                ],
                k=rng.randint(2, 4),
            ),
        )
    return docs


def generate() -> dict[str, list[dict]]:
    rng = random.Random(SEED)
    matters = list(MATTERS)
    categories = build_categories(rng)
    custodians = build_custodians(rng)
    return {
        "matters": matters,
        "subpoena_categories": categories,
        "production_logs": build_production_logs(rng, categories),
        "collection_events": build_collection_events(rng, custodians, categories),
        "retention_rules": build_retention_rules(rng),
        "destruction_events": build_destruction_events(rng),
        "privilege_logs": build_privilege_logs(rng, custodians, categories),
        "qc_events": build_qc_events(rng),
        "custodians": custodians,
        "documents": build_documents(rng, custodians, categories),
    }


def main() -> None:
    data = generate()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    generated_files = []
    for name, rows in data.items():
        path = DATA_DIR / f"{name}.json"
        dump_json(path, rows)
        generated_files.append(str(path.relative_to(BASE_DIR)))

    manifest = {
        "random_seed": SEED,
        "generation_timestamp": GENERATION_TIMESTAMP,
        "generated_files": generated_files,
        "record_counts": {name: len(rows) for name, rows in data.items()},
        "public_endpoints": ENDPOINTS,
        "service_start_command": "PORT=8057 ./setup.sh",
    }
    dump_json(MANIFEST_PATH, manifest)

    print(json.dumps(manifest["record_counts"], sort_keys=True))


if __name__ == "__main__":
    main()
