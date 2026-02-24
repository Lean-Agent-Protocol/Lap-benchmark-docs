#!/usr/bin/env python3
"""
Parse Claude Code JSONL session recordings for precise metrics.

JSONL files contain one JSON object per line, representing messages
in a Claude Code session. Each message has a type, role, and content.
"""

import json
from pathlib import Path


def parse_jsonl(path: str | Path) -> list[dict]:
    """Parse a JSONL file into a list of message dicts."""
    messages = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return messages


def extract_metrics(messages: list[dict]) -> dict:
    """Extract execution metrics from parsed JSONL messages.

    Returns:
        {
            turn_count: int,
            total_input_tokens: int,
            total_output_tokens: int,
            total_tokens: int,
            tool_calls: int,
            tool_names: list[str],
            has_error: bool,
            duration_ms: int | None,
        }
    """
    total_input = 0
    total_output = 0
    tool_calls = 0
    tool_names = []
    turns = 0
    has_error = False
    first_ts = None
    last_ts = None

    for msg in messages:
        # Track timestamps
        ts = msg.get("timestamp")
        if ts:
            if first_ts is None:
                first_ts = ts
            last_ts = ts

        # Count assistant turns
        if msg.get("role") == "assistant":
            turns += 1

        # Token usage
        usage = msg.get("usage", {})
        if usage:
            total_input += usage.get("input_tokens", 0)
            total_output += usage.get("output_tokens", 0)

        # Tool calls
        content = msg.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_use":
                        tool_calls += 1
                        name = block.get("name", "unknown")
                        tool_names.append(name)
                    if block.get("type") == "tool_result" and block.get("is_error"):
                        has_error = True

    duration_ms = None
    if first_ts and last_ts:
        try:
            duration_ms = int(last_ts - first_ts)
        except (TypeError, ValueError):
            pass

    return {
        "turn_count": turns,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "tool_calls": tool_calls,
        "tool_names": tool_names,
        "has_error": has_error,
        "duration_ms": duration_ms,
    }


def extract_agent_output(messages: list[dict]) -> str:
    """Extract the final assistant text output from a session."""
    last_text = ""
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", [])
        if isinstance(content, str):
            last_text = content
        elif isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            if text_parts:
                last_text = "\n".join(text_parts)
    return last_text


def parse_session_file(path: str | Path) -> dict:
    """Parse a JSONL session file and return all extracted data.

    Returns:
        {metrics: {...}, output: str, message_count: int}
    """
    messages = parse_jsonl(path)
    return {
        "metrics": extract_metrics(messages),
        "output": extract_agent_output(messages),
        "message_count": len(messages),
    }
