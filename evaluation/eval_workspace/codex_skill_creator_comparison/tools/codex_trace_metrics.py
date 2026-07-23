#!/usr/bin/env python3
"""Deterministic metrics extraction for Codex primary rollout traces.

This module intentionally accepts usage only from the final
event_msg.token_count.info.total_token_usage object. It never substitutes
last_token_usage or a recursively discovered usage dictionary.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


USAGE_KEYS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)


class TraceMetricsError(ValueError):
    """Raised when a primary trace cannot produce auditable metrics."""


def _usage_from_total_token_usage(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        raise TraceMetricsError("total_token_usage is not an object")
    usage: dict[str, int] = {}
    for key in USAGE_KEYS:
        item = value.get(key)
        if not isinstance(item, int) or isinstance(item, bool) or item < 0:
            raise TraceMetricsError(f"total_token_usage.{key} is not a non-negative integer")
        usage[key] = item
    if usage["total_tokens"] != usage["input_tokens"] + usage["output_tokens"]:
        raise TraceMetricsError("total_tokens does not equal input_tokens + output_tokens")
    if usage["cached_input_tokens"] > usage["input_tokens"]:
        raise TraceMetricsError("cached_input_tokens exceeds input_tokens")
    if usage["reasoning_output_tokens"] > usage["output_tokens"]:
        raise TraceMetricsError("reasoning_output_tokens exceeds output_tokens")
    return usage


def _record_id(payload: dict[str, Any]) -> str | None:
    for key in ("id", "message_id", "response_id", "item_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _tool_call_id(payload: dict[str, Any]) -> str | None:
    for key in ("call_id", "id", "item_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _model_candidates(record: dict[str, Any], payload: dict[str, Any]) -> Iterable[str]:
    for container in (record, payload, payload.get("info")):
        if not isinstance(container, dict):
            continue
        for key in ("model", "model_id", "model_name"):
            value = container.get(key)
            if isinstance(value, str) and value:
                yield value


def parse_codex_trace_records(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    final_total_usage: dict[str, int] | None = None
    response_message_ids: set[str] = set()
    response_messages_without_ids = 0
    event_message_ids: set[str] = set()
    event_messages_without_ids = 0
    tool_call_ids: set[str] = set()
    tool_calls_without_ids = 0
    observed_models: list[str] = []
    portability_warnings: set[str] = set()

    for record in records:
        if not isinstance(record, dict):
            raise TraceMetricsError("trace record is not an object")
        payload = record.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        record_type = record.get("type")
        payload_type = payload.get("type")

        if record_type == "event_msg" and payload_type == "token_count":
            info = payload.get("info")
            if not isinstance(info, dict):
                raise TraceMetricsError("token_count.info is not an object")
            if "total_token_usage" not in info:
                raise TraceMetricsError("token_count.info.total_token_usage is missing")
            final_total_usage = _usage_from_total_token_usage(info["total_token_usage"])

        if record_type == "response_item" and payload_type == "message" and payload.get("role") == "assistant":
            item_id = _record_id(payload)
            if item_id is None:
                response_messages_without_ids += 1
            else:
                response_message_ids.add(item_id)

        if record_type == "event_msg" and payload_type in {"agent_message", "assistant_message"}:
            item_id = _record_id(payload)
            if item_id is None:
                event_messages_without_ids += 1
            else:
                event_message_ids.add(item_id)

        if record_type == "response_item" and payload_type in {"function_call", "custom_tool_call"}:
            call_id = _tool_call_id(payload)
            if call_id is None:
                tool_calls_without_ids += 1
            else:
                tool_call_ids.add(call_id)

        observed_models.extend(_model_candidates(record, payload))

        serialized = json.dumps(record, ensure_ascii=False, sort_keys=True)
        if "/work/creator/" in serialized or "creator/" in serialized:
            for module in re.findall(r"ModuleNotFoundError: No module named [\\\"']([^\\\"']+)[\\\"']", serialized):
                portability_warnings.add(f"creator_tool_dependency_missing:{module}")

    if final_total_usage is None:
        raise TraceMetricsError("no event_msg.token_count.info.total_token_usage was found")

    response_turns = len(response_message_ids) + response_messages_without_ids
    event_turns = len(event_message_ids) + event_messages_without_ids
    assistant_turns = response_turns if response_turns else event_turns
    if assistant_turns <= 0:
        raise TraceMetricsError("no assistant responses were found")

    return {
        **final_total_usage,
        "usage_source": "final_token_count.info.total_token_usage",
        "assistant_turns": assistant_turns,
        "assistant_turn_source": (
            "response_item.message.role=assistant"
            if response_turns
            else "event_msg.agent_message"
        ),
        "tool_calls": len(tool_call_ids) + tool_calls_without_ids,
        "observed_model_identity": observed_models[-1] if observed_models else None,
        "portability_warnings": sorted(portability_warnings),
    }


def parse_codex_trace(path: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                value = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise TraceMetricsError(f"invalid JSON on line {line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise TraceMetricsError(f"trace line {line_number} is not an object")
            records.append(value)
    return parse_codex_trace_records(records)


def self_test() -> None:
    records = [
        {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "total_token_usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 80,
                        "output_tokens": 20,
                        "reasoning_output_tokens": 5,
                        "total_tokens": 120,
                    },
                    "last_token_usage": {
                        "input_tokens": 10,
                        "cached_input_tokens": 8,
                        "output_tokens": 2,
                        "reasoning_output_tokens": 1,
                        "total_tokens": 12,
                    },
                },
            },
        },
        {"type": "response_item", "payload": {"type": "message", "role": "assistant"}},
        {"type": "event_msg", "payload": {"type": "agent_message", "message": "duplicate view"}},
        {"type": "response_item", "payload": {"type": "function_call", "call_id": "call-1"}},
        {"type": "response_item", "payload": {"type": "function_call", "call_id": "call-1"}},
        {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "total_token_usage": {
                        "input_tokens": 300,
                        "cached_input_tokens": 240,
                        "output_tokens": 40,
                        "reasoning_output_tokens": 10,
                        "total_tokens": 340,
                    },
                    "last_token_usage": {
                        "input_tokens": 30,
                        "cached_input_tokens": 24,
                        "output_tokens": 4,
                        "reasoning_output_tokens": 1,
                        "total_tokens": 34,
                    },
                },
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "text": "creator command failed: /work/creator/scripts/init.py: "
                "ModuleNotFoundError: No module named 'yaml'",
            },
        },
        {"type": "response_item", "payload": {"type": "custom_tool_call", "call_id": "call-2"}},
    ]
    metrics = parse_codex_trace_records(records)
    expected = {
        "input_tokens": 300,
        "cached_input_tokens": 240,
        "output_tokens": 40,
        "reasoning_output_tokens": 10,
        "total_tokens": 340,
        "assistant_turns": 2,
        "tool_calls": 2,
    }
    for key, value in expected.items():
        if metrics.get(key) != value:
            raise TraceMetricsError(f"self-test mismatch for {key}: {metrics.get(key)} != {value}")
    if metrics["portability_warnings"] != ["creator_tool_dependency_missing:yaml"]:
        raise TraceMetricsError("self-test did not capture the creator dependency warning")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_test:
            self_test()
            print("codex_trace_metrics self-test: OK")
            return 0
        if args.trace is None:
            parser.error("TRACE is required unless --self-test is used")
        metrics = parse_codex_trace(args.trace)
        print(json.dumps(metrics, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
        return 0
    except (OSError, TraceMetricsError) as exc:
        print(f"codex_trace_metrics: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
