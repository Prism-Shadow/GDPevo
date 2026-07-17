#!/usr/bin/env python3
"""Generate the shared engineering operations data set."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


SEED = 2702401
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

CATEGORIES = ("NewFeature", "TechDebt", "Reliability", "Security")
TERMINAL_STATUSES = {"Done", "Closed", "Verified", "Cancelled"}
OPEN_STATUSES = {"New", "In Progress", "Blocked", "Review"}
ACTIVE_STATUSES = OPEN_STATUSES | {"Reopened"}

PRODUCTS = [
    {"name": "Identity Platform", "code": "IDP", "director": "Maya Stone"},
    {"name": "Payments", "code": "PAY", "director": "Jonah Price"},
    {"name": "Data Platform", "code": "DAT", "director": "Nina Hart"},
    {"name": "Edge Services", "code": "EDG", "director": "Owen Reed"},
    {"name": "Collaboration Suite", "code": "COL", "director": "Priya Vale"},
    {"name": "Mobile Platform", "code": "MOB", "director": "Leo Brooks"},
    {"name": "Core Services", "code": "COR", "director": "Iris Blake"},
    {"name": "Atlas Admin", "code": "ATL", "director": "Samira Wells"},
    {"name": "Observability Tools", "code": "OBS", "director": "Theo Grant"},
    {"name": "Internal Developer Portal", "code": "DEV", "director": "Clara Quinn"},
    {"name": "CRM Integrations", "code": "CRM", "director": "Marcus Flynn"},
]

PRODUCT_AREAS = {
    "Identity Platform": ["OAuth flow", "session broker", "tenant roles", "token rotation", "directory sync"],
    "Payments": ["ledger posting", "chargeback queue", "settlement batch", "risk scoring", "invoice webhook"],
    "Data Platform": ["warehouse sync", "schema registry", "query planner", "stream connector", "lineage graph"],
    "Edge Services": ["traffic router", "cache purge", "TLS edge", "regional failover", "rate limiter"],
    "Collaboration Suite": [
        "document canvas",
        "sharing panel",
        "presence service",
        "comment digest",
        "workspace search",
    ],
    "Mobile Platform": ["offline sync", "push delivery", "release channel", "crash capture", "mobile auth"],
    "Core Services": ["job scheduler", "configuration store", "service mesh", "message bus", "audit pipeline"],
    "Atlas Admin": ["admin console", "role templates", "tenant import", "policy editor", "approval queue"],
    "Observability Tools": ["metric ingest", "alert routing", "trace sampler", "dashboard export", "log archive"],
    "Internal Developer Portal": [
        "catalog sync",
        "template runner",
        "build insights",
        "developer docs",
        "service scorecard",
    ],
    "CRM Integrations": ["contact sync", "opportunity bridge", "account dedupe", "activity feed", "CRM webhook"],
}

OWNER_NAMES = {
    "IDP": ["Avery Chen", "Morgan Ellis", "Riley Shah", "Taylor Brooks"],
    "PAY": ["Jordan Lane", "Casey Moore", "Robin Patel", "Blair Santos"],
    "DAT": ["Alex Kim", "Emery Clark", "Harper Ng", "Drew Fisher"],
    "EDG": ["Jamie Moss", "Quinn Rivera", "Parker Hale", "Reese Donovan"],
    "COL": ["Dana Cole", "Skyler Finch", "Rowan Gray", "Kendall Pierce"],
    "MOB": ["Devon Park", "Ari Bell", "Sage Turner", "Milan Fox"],
    "COR": ["Hayden Scott", "Finley Ward", "Jules Warren", "Lennox Page"],
    "ATL": ["Cameron West", "Noel Bryant", "Elliot Cross", "Marin Hayes"],
    "OBS": ["Sydney North", "Kai Mason", "Tessa Green", "Remy Blake"],
    "DEV": ["Arden Lake", "Marlowe Dean", "Kris Rowan", "Shawn Dale"],
    "CRM": ["Bailey Ross", "Indigo Pierce", "Luca Miles", "Nico Flynn"],
}

ROLE_ORDER = ["Engineering Manager", "Staff Engineer", "Reliability Lead", "Security Engineer"]

RELEASE_DEFS = [
    {
        "release_id": "REL-IDP-2025Q4",
        "name": "Guardian Identity Q4",
        "product": "Identity Platform",
        "release_date": "2025-12-18",
        "readiness_target": 0.93,
        "release_train": "Guardian",
    },
    {
        "release_id": "REL-PAY-2026Q1",
        "name": "Ledger Flow 2026.1",
        "product": "Payments",
        "release_date": "2026-02-28",
        "readiness_target": 0.92,
        "release_train": "Ledger Flow",
    },
    {
        "release_id": "REL-ORION-38",
        "name": "Orion 3.8",
        "product": "Data Platform",
        "release_date": "2026-03-12",
        "readiness_target": 0.92,
        "release_train": "Orion",
    },
    {
        "release_id": "REL-EDGE-2026Q1",
        "name": "Lattice Edge 2026.1",
        "product": "Edge Services",
        "release_date": "2026-03-22",
        "readiness_target": 0.90,
        "release_train": "Lattice",
    },
    {
        "release_id": "REL-COL-2026Q2",
        "name": "Canvas Collaboration 2026.2",
        "product": "Collaboration Suite",
        "release_date": "2026-06-25",
        "readiness_target": 0.91,
        "release_train": "Canvas",
    },
    {
        "release_id": "REL-CORE-2026Q2",
        "name": "Halley Core Q2 Train",
        "product": "Core Services",
        "release_date": "2026-06-28",
        "readiness_target": 0.94,
        "release_train": "Halley",
    },
    {
        "release_id": "REL-VEGA-20",
        "name": "Vega 2.0",
        "product": "Mobile Platform",
        "release_date": "2026-06-30",
        "readiness_target": 0.90,
        "release_train": "Vega",
    },
    {
        "release_id": "REL-ATLAS-Q3",
        "name": "Atlas Admin Q3 Control Train",
        "product": "Atlas Admin",
        "release_date": "2026-07-15",
        "readiness_target": 0.93,
        "release_train": "Atlas Control",
    },
    {
        "release_id": "REL-OBS-2026Q2",
        "name": "Hubble Observability 2026.2",
        "product": "Observability Tools",
        "release_date": "2026-06-18",
        "readiness_target": 0.89,
        "release_train": "Hubble",
    },
]

MILESTONE_NAMES = [
    ("Scope Lock", -56, True),
    ("API Complete", -38, True),
    ("Integration Complete", -24, False),
    ("Security Review", -13, True),
    ("Launch Readiness", -4, True),
]

SLA_TARGETS = {
    "Reliability": {"S1": 2, "S2": 5, "S3": 10, "S4": 21},
    "Security": {"S1": 3, "S2": 7, "S3": 14, "S4": 30},
    "TechDebt": {"S1": 14, "S2": 30, "S3": 45, "S4": 60},
    "NewFeature": {"S1": 30, "S2": 45, "S3": 75, "S4": 90},
}

BLOCKER_TYPES = [
    "External Dependency",
    "Environment",
    "Security Review",
    "Capacity",
    "Design Decision",
    "Data Migration",
    "Vendor",
    "Ownership Gap",
]

CAUSE_TEXTS = {
    "External Dependency": [
        "Waiting on upstream API contract approval.",
        "Dependent service has not exposed the required event.",
        "Partner system certification window moved later.",
    ],
    "Environment": [
        "Staging environment is missing the required regional capacity.",
        "Test data refresh is delayed for shared validation tenants.",
        "Build lane is blocked by an infrastructure image mismatch.",
    ],
    "Security Review": [
        "Security review found an unresolved privilege boundary question.",
        "Threat model sign-off is pending for elevated access paths.",
        "Compliance evidence is incomplete for audit controls.",
    ],
    "Capacity": [
        "Load test shows capacity below the launch threshold.",
        "Queue depth increases above the operational guardrail.",
        "Shard allocation is not ready for peak regional traffic.",
    ],
    "Design Decision": [
        "Architecture decision is pending from the product council.",
        "The owner group has not selected the migration fallback path.",
        "Cross-team behavior remains ambiguous for rollback handling.",
    ],
    "Data Migration": [
        "Backfill validation is failing for historical tenant records.",
        "Migration checksum is not stable across dry-run attempts.",
        "Data retention exception needs explicit approval.",
    ],
    "Vendor": [
        "Vendor response is overdue for SDK compatibility details.",
        "Third-party incident delays final certification.",
        "Vendor test account is not available in the required region.",
    ],
    "Ownership Gap": [
        "No accountable owner is assigned for final production validation.",
        "Escalation is waiting for a service owner decision.",
        "Hand-off between teams left the follow-up queue unowned.",
    ],
}


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def date_string(value: date) -> str:
    return value.isoformat()


def timestamp(value: date, hour: int = 9, minute: int = 0) -> str:
    return datetime(value.year, value.month, value.day, hour, minute, 0).isoformat()


def quarter_for(value: date) -> str:
    quarter = ((value.month - 1) // 3) + 1
    return f"{value.year}-Q{quarter}"


def slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in value.lower()).strip("-")


def clamp_date(value: date, lower: date, upper: date) -> date:
    return max(lower, min(value, upper))


class Builder:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.teams = []
        self.owners = []
        self.work_items = []
        self.status_history = []
        self.dependencies = []
        self.blockers = []
        self.releases = []
        self.milestones = []
        self.milestone_items = []
        self.portfolio_targets = []
        self.sla_policies = []
        self.documents = []
        self.item_counter = 1
        self.blocker_counter = 1
        self.duplicate_counter = 1
        self.team_by_product = {}
        self.owners_by_team = defaultdict(list)
        self.release_by_id = {}
        self.milestones_by_release = defaultdict(list)
        self.item_by_id = {}
        self.item_meta = {}
        self.milestone_item_keys = set()
        self.dependency_keys = set()
        self.scope_items = defaultdict(list)
        self.construction_index = {
            "seed": seed,
            "scope_notes": "Hidden construction aid for task builders. This file is not served by the HTTP service.",
            "scopes": {},
            "notable_records": {},
        }

    def random_date(self, start: date, end: date) -> date:
        if end < start:
            return start
        delta = (end - start).days
        return start + timedelta(days=self.rng.randint(0, delta))

    def next_work_item_id(self) -> str:
        value = f"WI-{self.item_counter:04d}"
        self.item_counter += 1
        return value

    def next_blocker_id(self) -> str:
        value = f"BLK-{self.blocker_counter:04d}"
        self.blocker_counter += 1
        return value

    def next_duplicate_cluster_id(self) -> str:
        value = f"DUP-{self.duplicate_counter:03d}"
        self.duplicate_counter += 1
        return value

    def build_people(self) -> None:
        for product in PRODUCTS:
            team = {
                "team_id": f"TEAM-{product['code']}",
                "name": f"{product['name']} Engineering",
                "product_line": product["name"],
                "director": product["director"],
            }
            self.teams.append(team)
            self.team_by_product[product["name"]] = team
            for index, role in enumerate(ROLE_ORDER):
                owner = {
                    "owner_id": f"OWN-{product['code']}-{index + 1}",
                    "display_name": OWNER_NAMES[product["code"]][index],
                    "team_id": team["team_id"],
                    "role": role,
                }
                self.owners.append(owner)
                self.owners_by_team[team["team_id"]].append(owner)

    def build_releases(self) -> None:
        for release in RELEASE_DEFS:
            self.releases.append(dict(release))
            self.release_by_id[release["release_id"]] = release
            release_date = parse_date(release["release_date"])
            compact_id = release["release_id"].replace("REL-", "").replace("-", "")
            for index, (name, offset, critical) in enumerate(MILESTONE_NAMES, start=1):
                milestone = {
                    "milestone_id": f"MS-{compact_id}-{index:02d}",
                    "release_id": release["release_id"],
                    "name": name,
                    "target_date": date_string(release_date + timedelta(days=offset)),
                    "critical": critical,
                }
                self.milestones.append(milestone)
                self.milestones_by_release[release["release_id"]].append(milestone)

    def build_targets(self) -> None:
        target_profiles = {
            "Identity Platform": [45, 20, 20, 15],
            "Payments": [38, 18, 24, 20],
            "Data Platform": [35, 30, 20, 15],
            "Edge Services": [34, 22, 29, 15],
            "Collaboration Suite": [50, 20, 15, 15],
            "Mobile Platform": [42, 18, 24, 16],
            "Core Services": [35, 20, 25, 20],
            "Atlas Admin": [30, 25, 15, 30],
            "Observability Tools": [32, 28, 30, 10],
            "Internal Developer Portal": [46, 32, 14, 8],
            "CRM Integrations": [48, 22, 18, 12],
        }
        quarters = ["2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"]
        for product in target_profiles:
            base = target_profiles[product]
            for quarter in quarters:
                adjustments = [0, 0, 0, 0]
                if quarter == "2026-Q2":
                    adjustments = [0, -2, 1, 1]
                elif quarter == "2026-Q3":
                    adjustments = [-3, 1, 1, 1]
                values = [base[i] + adjustments[i] for i in range(4)]
                values[0] += 100 - sum(values)
                for category, target in zip(CATEGORIES, values):
                    self.portfolio_targets.append(
                        {
                            "product": product,
                            "quarter": quarter,
                            "category": category,
                            "target_percentage": target,
                        }
                    )

    def build_sla_policies(self) -> None:
        for category in CATEGORIES:
            for severity, target_days in SLA_TARGETS[category].items():
                self.sla_policies.append(
                    {
                        "category": category,
                        "severity": severity,
                        "target_days": target_days,
                        "applies_to_status": ["New", "In Progress", "Blocked", "Review", "Verified", "Closed", "Done"],
                    }
                )

    def build_documents(self) -> None:
        self.documents = [
            {
                "document_id": "DOC-CATEGORY-POLICY",
                "title": "Engineering Work Category Policy",
                "updated_date": "2026-01-10",
                "tags": ["portfolio", "classification", "work mix"],
                "body": (
                    "Portfolio reviews summarize completed engineering work across product delivery, platform investment, operational hardening, and security-oriented work. "
                    "Reviewers should use the available work item metadata consistently and reconcile unclear labels with the broader item context."
                ),
            },
            {
                "document_id": "DOC-SLA-POLICY",
                "title": "Reliability and Security SLA Aging Policy",
                "updated_date": "2026-02-01",
                "tags": ["sla", "aging", "triage"],
                "body": (
                    "SLA aging reviews combine work-item dates, severity, ownership, and queue state to identify operational risk. "
                    "Exports may require reconciliation across related records, and duplicate clusters are useful context for triage and audit."
                ),
            },
            {
                "document_id": "DOC-RELEASE-READINESS",
                "title": "Release Readiness Policy",
                "updated_date": "2026-02-18",
                "tags": ["release", "milestone", "readiness"],
                "body": (
                    "Release readiness reviews combine release records, milestones, work items, blockers, dependencies, owners, and team context. "
                    "The goal is to identify whether unresolved delivery risk remains before the release date and which work requires escalation."
                ),
            },
            {
                "document_id": "DOC-EXPORT-NOTES",
                "title": "Work Item Export Data Quality Notes",
                "updated_date": "2026-03-05",
                "tags": ["export", "status", "data quality"],
                "body": (
                    "The work item export is a periodic snapshot. Status export, owner assignment, labels, and release links can be stale or incomplete. "
                    "Analysts should compare available records when an operational review depends on the state of an item at a specific date."
                ),
            },
        ]

    def choose_owner(self, product: str, category: str, severity: str, missing_chance: float) -> str | None:
        if self.rng.random() < missing_chance:
            return None
        owners = self.owners_by_team[self.team_by_product[product]["team_id"]]
        if category == "Security":
            preferred = [owner for owner in owners if owner["role"] == "Security Engineer"]
        elif category == "Reliability":
            preferred = [owner for owner in owners if owner["role"] == "Reliability Lead"]
        elif severity in {"S1", "S2"}:
            preferred = [owner for owner in owners if owner["role"] in {"Staff Engineer", "Engineering Manager"}]
        else:
            preferred = owners
        return self.rng.choice(preferred or owners)["owner_id"]

    def category_template(
        self, category: str, product: str, area: str, duplicate_cluster: str | None
    ) -> tuple[str, str, list[str], str]:
        product_words = product.split()[0]
        if category == "Security":
            work_type = self.rng.choice(["Vulnerability", "Compliance", "Security"])
            title = self.rng.choice(
                [
                    f"Patch {area} vulnerability in {product_words}",
                    f"Harden {area} access control",
                    f"Complete compliance evidence for {area}",
                    f"Rotate exposed credential path for {area}",
                ]
            )
            labels = ["security", "vulnerability" if work_type == "Vulnerability" else "compliance"]
            description = (
                f"Security work for {area} with audit evidence, access-control review, and release validation."
            )
            if self.rng.random() < 0.22:
                labels.append("reliability")
        elif category == "Reliability":
            work_type = self.rng.choice(["Incident", "Reliability", "Bug"])
            title = self.rng.choice(
                [
                    f"Reduce {area} SLO breach rate",
                    f"Stabilize {area} retry storm",
                    f"Fix customer-impacting {area} incident",
                    f"Add failover guardrail for {area}",
                ]
            )
            labels = ["reliability", self.rng.choice(["slo", "incident", "capacity", "resiliency"])]
            description = (
                f"Reliability work for {area} covering operational alarms, SLO risk, and customer-impact analysis."
            )
            if self.rng.random() < 0.28:
                labels.append("tech-debt")
        elif category == "TechDebt":
            work_type = self.rng.choice(["Refactor", "Cleanup", "Migration", "Platform"])
            title = self.rng.choice(
                [
                    f"Refactor {area} service boundary",
                    f"Retire legacy {area} migration path",
                    f"Clean up internal {area} job flow",
                    f"Modernize {area} platform dependency",
                ]
            )
            labels = ["tech-debt", self.rng.choice(["cleanup", "migration", "internal", "platform"])]
            description = f"Internal modernization for {area}; the change reduces maintenance cost and simplifies future delivery."
            if self.rng.random() < 0.16:
                labels.append("reliability-review")
        else:
            work_type = self.rng.choice(["Feature", "Enhancement", "Experiment"])
            title = self.rng.choice(
                [
                    f"Add {area} guided workflow",
                    f"Launch {area} customer setting",
                    f"Expand {area} analytics panel",
                    f"Improve {area} onboarding path",
                ]
            )
            labels = ["feature", self.rng.choice(["customer", "enhancement", "growth", "workflow"])]
            description = f"Customer-facing delivery for {area} with product acceptance criteria and rollout notes."
        if duplicate_cluster:
            title = f"Duplicate signal {duplicate_cluster}: {title}"
            labels = sorted(set(labels + ["duplicate"]))
        return title, work_type, labels, description

    def choose_severity(self, category: str) -> str:
        if category == "Security":
            return self.rng.choices(["S1", "S2", "S3", "S4"], weights=[10, 35, 38, 17], k=1)[0]
        if category == "Reliability":
            return self.rng.choices(["S1", "S2", "S3", "S4"], weights=[14, 34, 36, 16], k=1)[0]
        if category == "TechDebt":
            return self.rng.choices(["S1", "S2", "S3", "S4"], weights=[2, 14, 45, 39], k=1)[0]
        return self.rng.choices(["S1", "S2", "S3", "S4"], weights=[1, 10, 44, 45], k=1)[0]

    def stale_status_for(self, effective_status: str) -> str:
        if effective_status in {"Closed", "Done", "Verified"}:
            return self.rng.choice(["In Progress", "Review", "Blocked"])
        if effective_status == "Cancelled":
            return self.rng.choice(["In Progress", "Review", "Closed"])
        if effective_status in {"Blocked", "Review", "In Progress"}:
            return self.rng.choice(["New", "Closed", "Done"])
        return self.rng.choice(["In Progress", "Review"])

    def add_history(self, work_item_id: str, created_date: date, updated_date: date, effective_status: str) -> None:
        span = max(0, (updated_date - created_date).days)
        events = [("New", created_date, "system")]
        if effective_status != "New" and span >= 1:
            events.append(
                ("In Progress", created_date + timedelta(days=max(1, min(span, span // 3 or 1))), "workflow")
            )
        if effective_status in {"Blocked", "Review", "Verified", "Done", "Closed"} and span >= 3:
            intermediate = "Blocked" if effective_status == "Blocked" else "Review"
            if intermediate != events[-1][0]:
                events.append(
                    (intermediate, created_date + timedelta(days=max(2, min(span, (span * 2) // 3 or 2))), "workflow")
                )
        if effective_status != events[-1][0]:
            events.append(
                (effective_status, updated_date, self.rng.choice(["workflow", "automation", "manual_update"]))
            )

        seen = set()
        for index, (status, event_date, source) in enumerate(events):
            event_date = clamp_date(event_date, created_date, updated_date)
            key = (status, event_date)
            if key in seen:
                continue
            seen.add(key)
            self.status_history.append(
                {
                    "work_item_id": work_item_id,
                    "status": status,
                    "timestamp": timestamp(event_date, 9 + (index % 8), (index * 7) % 60),
                    "source": source,
                }
            )

    def add_work_item(
        self,
        product: str,
        category: str,
        created_date: date,
        effective_status: str,
        *,
        updated_date: date | None = None,
        closed_date: date | None = None,
        due_date: date | None = None,
        release_ids: list[str] | None = None,
        target_area: str | None = None,
        duplicate_cluster: str | None = None,
        severity: str | None = None,
        owner_id: str | None | object = ...,
        labels_extra: list[str] | None = None,
        escaped: bool | None = None,
        customer_impact: bool | None = None,
        work_type: str | None = None,
        title: str | None = None,
        description: str | None = None,
        scope_tags: list[str] | None = None,
        stale_export_chance: float = 0.14,
        milestone_id: str | None = None,
        missing_owner_chance: float = 0.04,
    ) -> str:
        release_ids = list(release_ids or [])
        scope_tags = list(scope_tags or [])
        target_area = target_area or self.rng.choice(PRODUCT_AREAS[product])
        severity = severity or self.choose_severity(category)
        if due_date is None:
            due_date = created_date + timedelta(days=SLA_TARGETS[category][severity])
        if effective_status in TERMINAL_STATUSES:
            closed_date = closed_date or created_date + timedelta(days=self.rng.randint(4, 45))
            updated_date = updated_date or closed_date
        else:
            closed_date = None
            updated_date = updated_date or (created_date + timedelta(days=self.rng.randint(1, 45)))
        updated_date = max(created_date, updated_date)
        if owner_id is ...:
            owner_id = self.choose_owner(product, category, severity, missing_owner_chance)
        if title is None or description is None or work_type is None:
            generated_title, generated_work_type, labels, generated_description = self.category_template(
                category, product, target_area, duplicate_cluster
            )
            title = title or generated_title
            work_type = work_type or generated_work_type
            description = description or generated_description
        else:
            labels = []
        labels = sorted(set(labels + (labels_extra or []) + [slug(target_area)]))
        if escaped is None:
            escaped = category in {"Reliability", "Security"} and severity in {"S1", "S2"} and self.rng.random() < 0.28
        if customer_impact is None:
            customer_impact = category in {"Reliability", "Security"} and severity in {"S1", "S2", "S3"}
        status_export = effective_status
        if self.rng.random() < stale_export_chance:
            status_export = self.stale_status_for(effective_status)
        effective_anchor_date = closed_date if closed_date else updated_date
        item = {
            "id": self.next_work_item_id(),
            "title": title,
            "description": description,
            "product": product,
            "team_id": self.team_by_product[product]["team_id"],
            "owner_id": owner_id,
            "work_type": work_type,
            "labels": labels,
            "severity": severity,
            "status_export": status_export,
            "created_date": date_string(created_date),
            "updated_date": date_string(updated_date),
            "closed_date": date_string(closed_date) if closed_date else None,
            "due_date": date_string(due_date) if due_date else None,
            "quarter": quarter_for(effective_anchor_date),
            "release_ids": release_ids,
            "target_area": target_area,
            "duplicate_cluster": duplicate_cluster,
            "escaped": bool(escaped),
            "customer_impact": bool(customer_impact),
        }
        self.work_items.append(item)
        self.item_by_id[item["id"]] = item
        self.item_meta[item["id"]] = {
            "category": category,
            "effective_status": effective_status,
            "scope_tags": scope_tags,
        }
        self.add_history(item["id"], created_date, updated_date, effective_status)
        for scope in scope_tags:
            self.scope_items[scope].append(item["id"])
        if milestone_id:
            self.add_milestone_item(milestone_id, item["id"])
        return item["id"]

    def add_milestone_item(self, milestone_id: str, work_item_id: str) -> None:
        key = (milestone_id, work_item_id)
        if key in self.milestone_item_keys:
            return
        self.milestone_item_keys.add(key)
        self.milestone_items.append({"milestone_id": milestone_id, "work_item_id": work_item_id})

    def assign_missing_milestone_items(self) -> None:
        for item in self.work_items:
            for release_id in item["release_ids"]:
                milestones = self.milestones_by_release.get(release_id, [])
                if not milestones:
                    continue
                milestone = self.rng.choice(milestones)
                self.add_milestone_item(milestone["milestone_id"], item["id"])

    def add_dependency(self, upstream_id: str, downstream_id: str, dependency_type: str, critical: bool) -> None:
        if upstream_id == downstream_id:
            return
        key = (upstream_id, downstream_id, dependency_type)
        if key in self.dependency_keys:
            return
        self.dependency_keys.add(key)
        self.dependencies.append(
            {
                "upstream_id": upstream_id,
                "downstream_id": downstream_id,
                "dependency_type": dependency_type,
                "critical": bool(critical),
            }
        )

    def add_blocker(
        self,
        work_item_id: str,
        blocker_type: str | None = None,
        *,
        active: bool = True,
        created_date: date | None = None,
        resolved_date: date | None = None,
        severity: str | None = None,
    ) -> str:
        item = self.item_by_id[work_item_id]
        blocker_type = blocker_type or self.rng.choice(BLOCKER_TYPES)
        item_created = parse_date(item["created_date"])
        item_updated = parse_date(item["updated_date"])
        created_date = created_date or self.random_date(item_created, item_updated)
        if active:
            resolved_date = None
        elif resolved_date is None:
            resolved_date = created_date + timedelta(days=self.rng.randint(1, 18))
        blocker = {
            "blocker_id": self.next_blocker_id(),
            "work_item_id": work_item_id,
            "blocker_type": blocker_type,
            "cause_text": self.rng.choice(CAUSE_TEXTS[blocker_type]),
            "active": bool(active),
            "created_date": date_string(created_date),
            "resolved_date": date_string(resolved_date) if resolved_date else None,
            "severity": severity or item["severity"],
        }
        self.blockers.append(blocker)
        return blocker["blocker_id"]

    def make_scope_record(self, key: str, **values: object) -> None:
        self.construction_index["scopes"][key] = values


def add_portfolio_batch(
    builder: Builder,
    scope: str,
    product: str,
    quarter_start: str,
    quarter_end: str,
    counts: dict[str, int],
    release_id: str | None,
) -> None:
    start = parse_date(quarter_start)
    end = parse_date(quarter_end)
    for category, count in counts.items():
        for _ in range(count):
            closed = builder.random_date(start, end)
            created = closed - timedelta(days=builder.rng.randint(8, 72))
            status = builder.rng.choices(["Closed", "Done", "Verified"], weights=[50, 30, 20], k=1)[0]
            due_date = created + timedelta(
                days=SLA_TARGETS[category][builder.choose_severity(category)] + builder.rng.randint(-2, 12)
            )
            builder.add_work_item(
                product,
                category,
                created,
                status,
                closed_date=closed,
                due_date=due_date,
                release_ids=[release_id] if release_id and builder.rng.random() < 0.78 else [],
                scope_tags=[scope],
                stale_export_chance=0.20,
                missing_owner_chance=0.03 if category not in {"Security", "Reliability"} else 0.08,
            )
    builder.make_scope_record(
        scope,
        product=product,
        quarter=quarter_for(start),
        release_id=release_id,
        notable_work_item_ids=builder.scope_items[scope][:12],
        purpose="Portfolio work-mix construction scope.",
    )


def add_sla_batch(builder: Builder, scope: str, product: str, as_of: str, count: int, release_id: str | None) -> None:
    as_of_date = parse_date(as_of)
    for index in range(count):
        category = builder.rng.choice(["Reliability", "Security"])
        severity = builder.choose_severity(category)
        age = builder.rng.randint(1, 85)
        created = as_of_date - timedelta(days=age)
        status = builder.rng.choices(
            ["New", "In Progress", "Blocked", "Review", "Closed", "Done", "Verified"],
            weights=[8, 29, 24, 13, 10, 8, 8],
            k=1,
        )[0]
        closed = None
        updated = as_of_date - timedelta(days=builder.rng.randint(0, 18))
        if status in TERMINAL_STATUSES:
            recently_closed = builder.rng.random() < 0.72
            close_age = builder.rng.randint(0, 21 if recently_closed else 70)
            closed = as_of_date - timedelta(days=close_age)
            updated = closed
            created = min(created, closed - timedelta(days=builder.rng.randint(2, 55)))
        labels_extra = ["sla-review"]
        if index % 7 == 0:
            labels_extra.append("customer-escalation")
        builder.add_work_item(
            product,
            category,
            created,
            status,
            updated_date=updated,
            closed_date=closed,
            release_ids=[release_id] if release_id and builder.rng.random() < 0.32 else [],
            severity=severity,
            labels_extra=labels_extra,
            scope_tags=[scope],
            stale_export_chance=0.27,
            missing_owner_chance=0.18 if severity in {"S1", "S2"} else 0.07,
        )
    builder.make_scope_record(
        scope,
        product=product,
        as_of_date=as_of,
        release_id=release_id,
        notable_work_item_ids=builder.scope_items[scope][:14],
        purpose="SLA aging construction scope.",
    )


def add_duplicate_clusters(builder: Builder) -> None:
    cluster_plan = [
        ("Payments", "2026-02-15", 5, "sla_payments_2026_02_15", "REL-PAY-2026Q1"),
        ("Edge Services", "2026-04-10", 5, "sla_edge_services_2026_04_10", "REL-EDGE-2026Q1"),
        ("Mobile Platform", "2026-06-20", 6, "sla_mobile_platform_2026_06_20", "REL-VEGA-20"),
        ("Core Services", "2026-06-30", 2, "combined_core_services_q2_2026", "REL-CORE-2026Q2"),
        ("Observability Tools", "2026-06-05", 2, "distractor_observability_duplicates", "REL-OBS-2026Q2"),
        ("CRM Integrations", "2026-05-20", 2, "distractor_crm_duplicates", None),
        ("Identity Platform", "2025-12-12", 2, "distractor_identity_duplicates", "REL-IDP-2025Q4"),
    ]
    symptom_terms = [
        "timeout spike",
        "token refresh failure",
        "audit export drift",
        "regional failover alarm",
        "permission mismatch",
        "webhook replay loop",
        "cache eviction storm",
        "compliance evidence gap",
    ]
    for product, as_of, clusters, scope, release_id in cluster_plan:
        as_of_date = parse_date(as_of)
        for _ in range(clusters):
            cluster_id = builder.next_duplicate_cluster_id()
            category = builder.rng.choice(["Reliability", "Security"])
            symptom = builder.rng.choice(symptom_terms)
            item_count = builder.rng.choice([2, 3, 3, 4])
            for copy_index in range(item_count):
                severity = builder.choose_severity(category)
                created = as_of_date - timedelta(days=builder.rng.randint(4, 55))
                status = builder.rng.choices(
                    ["In Progress", "Blocked", "Review", "Closed", "Verified"], weights=[28, 28, 14, 18, 12], k=1
                )[0]
                closed = None
                updated = as_of_date - timedelta(days=builder.rng.randint(0, 12))
                if status in TERMINAL_STATUSES:
                    closed = as_of_date - timedelta(days=builder.rng.randint(0, 25))
                    updated = closed
                area = builder.rng.choice(PRODUCT_AREAS[product])
                title = f"Duplicate signal {cluster_id}: {symptom} on {area} variant {copy_index + 1}"
                description = (
                    f"Related report for {symptom} affecting {area}; duplicate cluster kept for operational audit."
                )
                builder.add_work_item(
                    product,
                    category,
                    created,
                    status,
                    updated_date=updated,
                    closed_date=closed,
                    release_ids=[release_id] if release_id and builder.rng.random() < 0.45 else [],
                    target_area=area,
                    duplicate_cluster=cluster_id,
                    severity=severity,
                    title=title,
                    description=description,
                    work_type="Incident" if category == "Reliability" else "Vulnerability",
                    labels_extra=["duplicate", "customer-signal", slug(symptom)],
                    scope_tags=[scope],
                    stale_export_chance=0.30,
                    missing_owner_chance=0.17,
                )


def add_release_batch(
    builder: Builder,
    scope: str,
    release_id: str,
    count: int,
    gate_count: int,
) -> None:
    release = builder.release_by_id[release_id]
    product = release["product"]
    release_date = parse_date(release["release_date"])
    critical_milestones = [m for m in builder.milestones_by_release[release_id] if m["critical"]]
    all_milestones = builder.milestones_by_release[release_id]
    gate_ids = []
    for gate_index in range(gate_count):
        category = builder.rng.choice(["Reliability", "Security"])
        created = release_date - timedelta(days=builder.rng.randint(36, 74))
        updated = release_date - timedelta(days=builder.rng.randint(3, 18))
        milestone = builder.rng.choice(critical_milestones)
        item_id = builder.add_work_item(
            product,
            category,
            created,
            "Blocked",
            updated_date=updated,
            release_ids=[release_id],
            severity=builder.rng.choice(["S1", "S2"]),
            labels_extra=["release-gate", "critical-path"],
            scope_tags=[scope],
            stale_export_chance=0.35,
            milestone_id=milestone["milestone_id"],
            missing_owner_chance=0.10,
        )
        gate_ids.append(item_id)
    for _ in range(count - gate_count):
        category = builder.rng.choices(CATEGORIES, weights=[36, 23, 24, 17], k=1)[0]
        created = release_date - timedelta(days=builder.rng.randint(28, 100))
        status = builder.rng.choices(
            ["Done", "Closed", "Verified", "In Progress", "Review", "Blocked", "Cancelled"],
            weights=[22, 24, 15, 16, 9, 8, 6],
            k=1,
        )[0]
        closed = None
        updated = release_date - timedelta(days=builder.rng.randint(1, 24))
        if status in TERMINAL_STATUSES:
            closed = release_date - timedelta(days=builder.rng.randint(1, 28))
            updated = closed
        milestone = builder.rng.choice(all_milestones)
        builder.add_work_item(
            product,
            category,
            created,
            status,
            updated_date=updated,
            closed_date=closed,
            release_ids=[release_id],
            labels_extra=["release-scope"],
            scope_tags=[scope],
            stale_export_chance=0.18,
            milestone_id=milestone["milestone_id"],
            missing_owner_chance=0.06,
        )
    builder.make_scope_record(
        scope,
        product=product,
        release_id=release_id,
        release_name=release["name"],
        notable_gate_candidates=gate_ids,
        notable_work_item_ids=builder.scope_items[scope][:16],
        purpose="Release readiness construction scope.",
    )


def add_random_distractors(builder: Builder, count: int) -> None:
    product_names = [product["name"] for product in PRODUCTS]
    release_ids = [release["release_id"] for release in RELEASE_DEFS]
    for index in range(count):
        product = builder.rng.choice(product_names)
        category = builder.rng.choices(CATEGORIES, weights=[34, 25, 25, 16], k=1)[0]
        created = builder.random_date(parse_date("2025-07-01"), parse_date("2026-07-05"))
        status = builder.rng.choices(
            ["New", "In Progress", "Blocked", "Review", "Done", "Closed", "Verified", "Cancelled"],
            weights=[5, 18, 12, 8, 16, 18, 14, 9],
            k=1,
        )[0]
        closed = None
        updated = created + timedelta(days=builder.rng.randint(1, 80))
        if status in TERMINAL_STATUSES:
            closed = updated
        release_ids_for_item = []
        if builder.rng.random() < 0.34:
            matching_releases = [release["release_id"] for release in RELEASE_DEFS if release["product"] == product]
            release_ids_for_item = [builder.rng.choice(matching_releases or release_ids)]
        builder.add_work_item(
            product,
            category,
            created,
            status,
            updated_date=updated,
            closed_date=closed,
            release_ids=release_ids_for_item,
            labels_extra=["distractor"] if index % 5 == 0 else [],
            stale_export_chance=0.18,
            missing_owner_chance=0.07,
        )


def add_dependencies(builder: Builder) -> None:
    for scope in ["release_orion_3_8", "release_vega_2_0", "release_atlas_admin_train"]:
        item_ids = builder.scope_items[scope]
        blocked = [item_id for item_id in item_ids if builder.item_meta[item_id]["effective_status"] == "Blocked"]
        incomplete = [
            item_id
            for item_id in item_ids
            if builder.item_meta[item_id]["effective_status"] in {"In Progress", "Review", "Blocked", "New"}
        ]
        complete = [
            item_id
            for item_id in item_ids
            if builder.item_meta[item_id]["effective_status"] in {"Done", "Closed", "Verified"}
        ]
        chains = []
        for index, upstream in enumerate(blocked[:3]):
            downstream_pool = [item_id for item_id in incomplete + complete if item_id != upstream]
            if downstream_pool:
                downstream = downstream_pool[(index * 3) % len(downstream_pool)]
                builder.add_dependency(upstream, downstream, "blocks", True)
                chains.append([upstream, downstream])
        if len(incomplete) >= 2 and complete:
            builder.add_dependency(incomplete[0], incomplete[1], "requires", True)
            builder.add_dependency(incomplete[1], complete[0], "blocks", False)
            chains.extend([[incomplete[0], incomplete[1]], [incomplete[1], complete[0]]])
        builder.construction_index["scopes"][scope]["critical_dependency_examples"] = chains[:5]

    by_release = defaultdict(list)
    by_product = defaultdict(list)
    for item in builder.work_items:
        by_product[item["product"]].append(item["id"])
        for release_id in item["release_ids"]:
            by_release[release_id].append(item["id"])

    attempts = 0
    while len(builder.dependencies) < 86 and attempts < 1000:
        attempts += 1
        if builder.rng.random() < 0.65:
            release_pool = builder.rng.choice([ids for ids in by_release.values() if len(ids) >= 2])
            upstream, downstream = builder.rng.sample(release_pool, 2)
        else:
            product_pool = builder.rng.choice([ids for ids in by_product.values() if len(ids) >= 2])
            upstream, downstream = builder.rng.sample(product_pool, 2)
        builder.add_dependency(
            upstream,
            downstream,
            builder.rng.choice(["blocks", "requires", "duplicates_signal", "validates"]),
            builder.rng.random() < 0.34,
        )


def add_blockers(builder: Builder) -> None:
    blocked_items = [item_id for item_id, meta in builder.item_meta.items() if meta["effective_status"] == "Blocked"]
    active_candidates = blocked_items[:]
    builder.rng.shuffle(active_candidates)
    for item_id in active_candidates[:38]:
        preferred_type = "Security Review" if builder.item_meta[item_id]["category"] == "Security" else None
        if item_id in builder.construction_index["scopes"].get("release_orion_3_8", {}).get(
            "notable_gate_candidates", []
        ):
            preferred_type = builder.rng.choice(["Capacity", "Data Migration", "Security Review"])
        if item_id in builder.construction_index["scopes"].get("release_vega_2_0", {}).get(
            "notable_gate_candidates", []
        ):
            preferred_type = builder.rng.choice(["External Dependency", "Environment", "Vendor"])
        if item_id in builder.construction_index["scopes"].get("release_atlas_admin_train", {}).get(
            "notable_gate_candidates", []
        ):
            preferred_type = builder.rng.choice(["Security Review", "Ownership Gap", "Design Decision"])
        builder.add_blocker(item_id, preferred_type, active=True)

    non_blocked = [
        item["id"]
        for item in builder.work_items
        if builder.item_meta[item["id"]]["effective_status"] in {"In Progress", "Review", "Closed", "Done", "Verified"}
    ]
    builder.rng.shuffle(non_blocked)
    for item_id in non_blocked[:24]:
        item = builder.item_by_id[item_id]
        created = parse_date(item["created_date"]) + timedelta(days=builder.rng.randint(1, 12))
        active = (
            builder.item_meta[item_id]["effective_status"] in {"In Progress", "Review"} and builder.rng.random() < 0.35
        )
        builder.add_blocker(
            item_id,
            builder.rng.choice(BLOCKER_TYPES),
            active=active,
            created_date=created,
            resolved_date=None if active else created + timedelta(days=builder.rng.randint(2, 20)),
        )

    if len(builder.blockers) < 48:
        remaining = [item["id"] for item in builder.work_items]
        while len(builder.blockers) < 48:
            builder.add_blocker(builder.rng.choice(remaining), active=builder.rng.random() < 0.5)


def build_dataset() -> Builder:
    builder = Builder(SEED)
    builder.build_people()
    builder.build_releases()
    builder.build_targets()
    builder.build_sla_policies()
    builder.build_documents()

    add_portfolio_batch(
        builder,
        "portfolio_identity_q4_2025",
        "Identity Platform",
        "2025-10-01",
        "2025-12-31",
        {"NewFeature": 13, "TechDebt": 7, "Reliability": 6, "Security": 5},
        "REL-IDP-2025Q4",
    )
    add_portfolio_batch(
        builder,
        "portfolio_data_platform_q1_2026",
        "Data Platform",
        "2026-01-01",
        "2026-03-31",
        {"NewFeature": 10, "TechDebt": 11, "Reliability": 7, "Security": 5},
        "REL-ORION-38",
    )
    add_portfolio_batch(
        builder,
        "portfolio_collaboration_suite_q2_2026",
        "Collaboration Suite",
        "2026-04-01",
        "2026-06-30",
        {"NewFeature": 17, "TechDebt": 8, "Reliability": 6, "Security": 5},
        "REL-COL-2026Q2",
    )
    add_portfolio_batch(
        builder,
        "combined_core_services_q2_2026",
        "Core Services",
        "2026-04-01",
        "2026-06-30",
        {"NewFeature": 9, "TechDebt": 6, "Reliability": 9, "Security": 6},
        "REL-CORE-2026Q2",
    )
    add_portfolio_batch(
        builder,
        "portfolio_atlas_admin_release_scope",
        "Atlas Admin",
        "2026-04-01",
        "2026-06-30",
        {"NewFeature": 8, "TechDebt": 7, "Reliability": 5, "Security": 10},
        "REL-ATLAS-Q3",
    )

    add_sla_batch(builder, "sla_payments_2026_02_15", "Payments", "2026-02-15", 30, "REL-PAY-2026Q1")
    add_sla_batch(builder, "sla_edge_services_2026_04_10", "Edge Services", "2026-04-10", 28, "REL-EDGE-2026Q1")
    add_sla_batch(builder, "sla_mobile_platform_2026_06_20", "Mobile Platform", "2026-06-20", 34, "REL-VEGA-20")
    add_sla_batch(builder, "combined_core_services_q2_2026", "Core Services", "2026-06-30", 22, "REL-CORE-2026Q2")

    add_duplicate_clusters(builder)

    add_release_batch(builder, "release_orion_3_8", "REL-ORION-38", 28, 4)
    add_release_batch(builder, "release_vega_2_0", "REL-VEGA-20", 30, 5)
    add_release_batch(builder, "release_atlas_admin_train", "REL-ATLAS-Q3", 28, 5)
    add_release_batch(builder, "release_collaboration_canvas_2026_2", "REL-COL-2026Q2", 16, 2)
    add_release_batch(builder, "release_payments_ledger_2026_1", "REL-PAY-2026Q1", 15, 1)

    add_random_distractors(builder, 64)

    builder.assign_missing_milestone_items()
    add_dependencies(builder)
    add_blockers(builder)

    duplicate_clusters = sorted(
        {item["duplicate_cluster"] for item in builder.work_items if item["duplicate_cluster"]}
    )
    builder.construction_index["notable_records"] = {
        "duplicate_clusters": duplicate_clusters,
        "stale_status_export_item_ids": [
            item["id"]
            for item in builder.work_items
            if item["status_export"] != builder.item_meta[item["id"]]["effective_status"]
        ][:60],
        "missing_owner_item_ids": [item["id"] for item in builder.work_items if item["owner_id"] is None][:60],
    }
    for scope, item_ids in builder.scope_items.items():
        if scope not in builder.construction_index["scopes"]:
            builder.make_scope_record(scope, notable_work_item_ids=item_ids[:12])
        else:
            builder.construction_index["scopes"][scope].setdefault("notable_work_item_ids", item_ids[:12])

    return builder


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_dataset(builder: Builder) -> dict[str, int]:
    tables = {
        "teams.json": builder.teams,
        "owners.json": builder.owners,
        "work_items.json": builder.work_items,
        "status_history.json": sorted(builder.status_history, key=lambda row: (row["work_item_id"], row["timestamp"])),
        "dependencies.json": builder.dependencies,
        "blockers.json": builder.blockers,
        "releases.json": builder.releases,
        "milestones.json": builder.milestones,
        "milestone_items.json": builder.milestone_items,
        "portfolio_targets.json": builder.portfolio_targets,
        "sla_policies.json": builder.sla_policies,
        "documents.json": builder.documents,
        "construction_index.json": builder.construction_index,
    }
    for filename, records in tables.items():
        write_json(DATA_DIR / filename, records)

    duplicate_cluster_count = len(
        {item["duplicate_cluster"] for item in builder.work_items if item["duplicate_cluster"]}
    )
    stale_status_conflicts = sum(
        1 for item in builder.work_items if item["status_export"] != builder.item_meta[item["id"]]["effective_status"]
    )
    counts = {
        "teams": len(builder.teams),
        "owners": len(builder.owners),
        "work_items": len(builder.work_items),
        "status_history": len(builder.status_history),
        "dependencies": len(builder.dependencies),
        "blockers": len(builder.blockers),
        "releases": len(builder.releases),
        "milestones": len(builder.milestones),
        "milestone_items": len(builder.milestone_items),
        "portfolio_targets": len(builder.portfolio_targets),
        "sla_policies": len(builder.sla_policies),
        "documents": len(builder.documents),
        "duplicate_clusters": duplicate_cluster_count,
        "stale_status_conflicts": stale_status_conflicts,
    }
    manifest = {
        "seed": SEED,
        "generated_files": sorted(str(Path("data") / filename) for filename in tables),
        "record_counts": counts,
        "public_endpoint_summary": [
            "GET /",
            "GET /health",
            "GET /web/dashboard",
            "GET /web/policies",
            "GET /api/teams",
            "GET /api/owners",
            "GET /api/work-items",
            "GET /api/work-items?product=<name>&quarter=<quarter>&status=<status>&category_hint=<hint>&release_id=<id>",
            "GET /api/work-items/<id>",
            "GET /api/status-history?work_item_id=<id>",
            "GET /api/status-history?product=<name>",
            "GET /api/dependencies",
            "GET /api/dependencies?release_id=<id>",
            "GET /api/blockers",
            "GET /api/blockers?release_id=<id>&active=true",
            "GET /api/releases",
            "GET /api/releases/<release_id>",
            "GET /api/milestones?release_id=<release_id>",
            "GET /api/milestone-items?release_id=<release_id>",
            "GET /api/portfolio-targets?product=<name>&quarter=<quarter>",
            "GET /api/sla-policies",
            "GET /api/search?q=<text>",
        ],
        "setup_command": "TASK_ENV_BIND=0.0.0.0 TASK_ENV_PORT=9024 ./setup.sh",
    }
    write_json(ROOT / "manifest.json", manifest)
    return counts


def main() -> None:
    builder = build_dataset()
    counts = write_dataset(builder)
    print(json.dumps({"seed": SEED, "record_counts": counts}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
