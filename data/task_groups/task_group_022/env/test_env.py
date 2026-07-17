#!/usr/bin/env python3
"""Focused integration checks for the Atlas HTTP service."""

from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
API_TOKEN = "atlas-ops-token-022"
OPERATOR_TOKEN = "atlas-operator-022"


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


class ServiceProcess:
    def __init__(self, database: Path, judge: bool):
        self.port = available_port()
        environment = os.environ.copy()
        environment.update({
            "TASK_ENV_BIND": "127.0.0.1",
            "TASK_ENV_PORT": str(self.port),
            "TASK_ENV_DATABASE": str(database),
            "TASK_ENV_BASELINE": str(HERE / "atlas_baseline.sqlite3"),
            "TASK_ENV_ENABLE_JUDGE": "1" if judge else "0",
            "TASK_ENV_API_TOKEN": API_TOKEN,
            "TASK_ENV_OPERATOR_TOKEN": OPERATOR_TOKEN,
        })
        self.process = subprocess.Popen(
            [sys.executable, str(HERE / "app.py")],
            cwd=HERE,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                raise RuntimeError(f"service exited during startup: {stdout} {stderr}")
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=0.2).read()
                break
            except (OSError, urllib.error.URLError):
                time.sleep(0.05)
        else:
            self.close()
            raise RuntimeError("service did not become healthy")

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.process.stdout:
            self.process.stdout.close()
        if self.process.stderr:
            self.process.stderr.close()


class AtlasEnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory(prefix="atlas-env-test-")
        cls.database = Path(cls.tempdir.name) / "runtime.sqlite3"
        shutil.copyfile(HERE / "atlas_baseline.sqlite3", cls.database)
        cls.manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
        cls.faults = cls.manifest["construction_only_fixtures"]["planted_carrier_faults"]
        cls.inventory_faults = cls.manifest["construction_only_fixtures"]["planted_inventory_faults"]
        cls.service = ServiceProcess(cls.database, judge=False)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.service.close()
        cls.tempdir.cleanup()

    def request(self, method: str, path: str, body: Any = None, token: str | None = API_TOKEN, expected: int = 200) -> dict[str, Any]:
        headers: dict[str, str] = {}
        data = None
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(f"http://127.0.0.1:{self.service.port}{path}", data=data, method=method, headers=headers)
        try:
            response = urllib.request.urlopen(request, timeout=10)
            status = response.status
            payload = json.loads(response.read())
        except urllib.error.HTTPError as error:
            status = error.code
            payload = json.loads(error.read())
        self.assertEqual(expected, status, payload)
        return payload

    def sql(self, sql: str, params: list[Any] | None = None, expected: int = 200) -> dict[str, Any]:
        return self.request("POST", "/api/sql", {"sql": sql, "params": params or []}, expected=expected)

    def test_01_health_schema_dictionary_and_auth(self) -> None:
        health = self.request("GET", "/health", token=None)
        self.assertEqual({"status", "schema_version"}, set(health))
        unauthorized = self.request("GET", "/api/schema", token=None, expected=401)
        self.assertEqual({"error": "unauthorized"}, unauthorized)
        schema = self.request("GET", "/api/schema")
        self.assertEqual(21, len(schema["tables"]))
        dictionary = self.request("GET", "/api/data-dictionary")
        self.assertEqual(21, len(dictionary["tables"]))
        self.assertIn("timestamps", dictionary["conventions"])

    def test_02_select_params_and_cap(self) -> None:
        result = self.sql("SELECT account_id, region FROM accounts WHERE region = ? ORDER BY account_id LIMIT 3", ["WEST"])
        self.assertEqual(["account_id", "region"], result["columns"])
        self.assertEqual(3, result["row_count"])
        capped = self.sql("SELECT event_id FROM order_events ORDER BY event_id")
        self.assertEqual(5000, capped["row_count"])
        self.assertTrue(capped["truncated"])

    def test_03_forbidden_sql_is_rejected(self) -> None:
        rejected = [
            "PRAGMA table_info(accounts)",
            "SELECT 1; SELECT 2",
            "SELECT 1 -- comment",
            "DELETE FROM accounts",
            "WITH changed AS (DELETE FROM accounts RETURNING *) SELECT * FROM changed",
            "SELECT load_extension(?)",
        ]
        for statement in rejected:
            with self.subTest(statement=statement):
                self.sql(statement, ["x"] if "?" in statement else [], expected=400)

    def test_04_valid_atomic_correction(self) -> None:
        fault = self.faults[1]
        self.assertEqual("canonical_status", fault["field"])
        payload = {
            "statements": [
                {
                    "sql": "UPDATE carrier_scans SET canonical_status = ?, corrected_at = ?, correction_reason = ? WHERE scan_row_id = ? AND canonical_status = ?",
                    "params": [fault["expected_value"], "2026-07-16T12:00:00Z", "SOURCE_RECONCILIATION", fault["scan_row_id"], fault["old_value"]],
                },
                {
                    "sql": "INSERT INTO correction_audit (audit_id, correction_key, entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code, corrected_at, actor) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    "params": ["AUD-TEST-VALID", "CK-TEST-VALID", "carrier_scan", fault["shipment_id"], fault["scan_row_id"], "canonical_status", fault["old_value"], fault["expected_value"], "SOURCE_RECONCILIATION", "2026-07-16T12:00:00Z", "integration-test"],
                },
                {
                    "sql": "SELECT canonical_status, corrected_at FROM carrier_scans WHERE scan_row_id = ?",
                    "params": [fault["scan_row_id"]],
                },
            ],
            "expected_total_changes": 2,
        }
        result = self.request("POST", "/api/sql/transaction", payload)
        self.assertEqual(2, result["total_changes"])
        self.assertEqual(fault["expected_value"], result["statements"][2]["rows"][0][0])
        audit = self.request("GET", f"/api/correction-audit?source_row_id={fault['scan_row_id']}")
        self.assertEqual(1, audit["row_count"])
        self.request("POST", "/api/sql/transaction", payload, expected=409)
        retry_audit = self.request("GET", f"/api/correction-audit?source_row_id={fault['scan_row_id']}")
        self.assertEqual(1, retry_audit["row_count"])

    def test_05_change_mismatch_rolls_back(self) -> None:
        fault = self.faults[3]
        payload = {
            "statements": [
                {
                    "sql": "UPDATE carrier_scans SET canonical_status = ?, corrected_at = ?, correction_reason = ? WHERE scan_row_id = ? AND canonical_status = ?",
                    "params": [fault["expected_value"], "2026-07-16T12:05:00Z", "SOURCE_RECONCILIATION", fault["scan_row_id"], fault["old_value"]],
                },
                {
                    "sql": "INSERT INTO correction_audit (audit_id, correction_key, entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code, corrected_at, actor) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    "params": ["AUD-TEST-ROLLBACK", "CK-TEST-ROLLBACK", "carrier_scan", fault["shipment_id"], fault["scan_row_id"], "canonical_status", fault["old_value"], fault["expected_value"], "SOURCE_RECONCILIATION", "2026-07-16T12:05:00Z", "integration-test"],
                },
            ],
            "expected_total_changes": 3,
        }
        self.request("POST", "/api/sql/transaction", payload, expected=409)
        row = self.sql("SELECT canonical_status, corrected_at FROM carrier_scans WHERE scan_row_id = ?", [fault["scan_row_id"]])
        self.assertEqual([fault["old_value"], None], row["rows"][0])
        audit = self.request("GET", "/api/correction-audit?source_row_id=" + fault["scan_row_id"])
        self.assertEqual(0, audit["row_count"])

    def test_06_guard_rejections(self) -> None:
        invalid_payloads = [
            {"sql": "UPDATE carrier_scans SET canonical_status = ? WHERE canonical_status = ?", "params": ["DELIVERED", "IN_TRANSIT"]},
            {"sql": "UPDATE carrier_scans SET raw_status = ? WHERE scan_row_id = ? AND raw_status = ?", "params": ["X", "SCN-1", "Y"]},
            {"sql": "DELETE FROM carrier_scans WHERE scan_row_id = ?", "params": ["SCN-1"]},
        ]
        for statement in invalid_payloads:
            with self.subTest(sql=statement["sql"]):
                payload = {"statements": [statement], "expected_total_changes": 1}
                self.request("POST", "/api/sql/transaction", payload, expected=400)

    def test_07_inventory_correction_interface(self) -> None:
        fault = self.inventory_faults[0]
        payload = {
            "statements": [
                {
                    "sql": "UPDATE inventory_movements SET canonical_quantity_each = ?, canonical_uom_multiplier = ?, corrected_at = ?, correction_reason = ? WHERE movement_row_id = ? AND canonical_quantity_each = ? AND canonical_uom_multiplier = ?",
                    "params": [fault["expected_quantity_each"], fault["expected_multiplier"], "2026-07-16T12:10:00Z", "UOM_RECONCILIATION", fault["movement_row_id"], fault["old_quantity_each"], fault["old_multiplier"]],
                },
                {
                    "sql": "INSERT INTO correction_audit (audit_id, correction_key, entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code, corrected_at, actor) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    "params": ["AUD-TEST-INVENTORY", "CK-TEST-INVENTORY", "inventory_movement", fault["movement_id"], fault["movement_row_id"], "canonical_uom_multiplier", str(fault["old_multiplier"]), str(fault["expected_multiplier"]), "UOM_RECONCILIATION", "2026-07-16T12:10:00Z", "integration-test"],
                },
            ],
            "expected_total_changes": 2,
        }
        result = self.request("POST", "/api/sql/transaction", payload)
        self.assertEqual(2, result["total_changes"])
        row = self.sql("SELECT canonical_quantity_each, canonical_uom_multiplier FROM inventory_movements WHERE movement_row_id = ?", [fault["movement_row_id"]])
        self.assertEqual([fault["expected_quantity_each"], fault["expected_multiplier"]], row["rows"][0])

    def test_08_reset_restores_baseline(self) -> None:
        fault = self.faults[1]
        reset = self.request("POST", "/api/operator/reset", {}, token=OPERATOR_TOKEN)
        self.assertEqual({"status": "reset", "schema_version": "atlas-commerce-1.0"}, reset)
        row = self.sql("SELECT canonical_status, corrected_at FROM carrier_scans WHERE scan_row_id = ?", [fault["scan_row_id"]])
        self.assertEqual([fault["old_value"], None], row["rows"][0])
        audit = self.request("GET", "/api/correction-audit")
        self.assertEqual(0, audit["row_count"])

    def test_09_judge_disabled_then_enabled(self) -> None:
        self.request("POST", "/api/judge", {"task_id": "train_001", "answer": {}}, expected=404)
        self.service.close()
        self.__class__.service = ServiceProcess(self.database, judge=True)
        standard = json.loads((HERE / "judge_answers" / "train_001.json").read_text(encoding="utf-8"))
        result = self.request("POST", "/api/judge", {"task_id": "train_001", "answer": standard})
        self.assertEqual({"score", "correct", "notice"}, set(result))
        self.assertEqual(1.0, result["score"])
        self.assertTrue(result["correct"])
        self.assertEqual("train-only judge", result["notice"])
        standard["on_time_complete_order_rate"] += 0.0001
        partial = self.request("POST", "/api/judge", {"task_id": "train_001", "answer": standard})
        self.assertEqual(0.8125, partial["score"])
        self.assertFalse(partial["correct"])
        self.request("POST", "/api/judge", {"task_id": "test_001", "answer": {}}, expected=400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
