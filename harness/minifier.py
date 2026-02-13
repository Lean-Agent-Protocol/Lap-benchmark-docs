#!/usr/bin/env python3
"""
Format-aware minifier for API specifications.

Strips comments, blank lines, and unnecessary whitespace while preserving
spec validity. Each format has its own minification strategy.
"""

import json
import re
import sys
from pathlib import Path


def minify_yaml(text: str) -> str:
    """Minify YAML (OpenAPI/AsyncAPI): parse then re-serialize compactly.

    This avoids comment-stripping edge cases by round-tripping through
    the YAML parser, which drops comments and normalizes formatting.
    """
    import yaml

    data = yaml.safe_load(text)
    return yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        width=10000,  # avoid line wrapping
        sort_keys=False,
    )


def minify_json(text: str) -> str:
    """Minify JSON (Postman): compact serialization."""
    data = json.loads(text)
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def minify_graphql(text: str) -> str:
    """Minify GraphQL: strip comments, collapse whitespace."""
    lines = []
    for line in text.splitlines():
        # Remove single-line comments (# ...)
        comment_pos = _find_graphql_comment(line)
        if comment_pos is not None:
            line = line[:comment_pos]
        line = line.rstrip()
        if not line.strip():
            continue
        lines.append(line)

    result = "\n".join(lines)
    # Collapse runs of whitespace (but keep newlines for readability)
    result = re.sub(r"[ \t]+", " ", result)
    # Remove spaces around structural chars
    result = re.sub(r"\s*([{}()\[\]:,!])\s*", r"\1", result)
    # Ensure newline after { and before }
    result = re.sub(r"\{", "{\n", result)
    result = re.sub(r"\}", "\n}", result)
    # Clean up multiple newlines
    result = re.sub(r"\n{2,}", "\n", result)
    return result.strip() + "\n"


def _find_graphql_comment(line: str) -> int | None:
    """Find position of # comment in GraphQL line (not inside strings)."""
    in_string = False
    escape = False
    for i, ch in enumerate(line):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
        elif ch == "#" and not in_string:
            return i
    return None


def minify_protobuf(text: str) -> str:
    """Minify Protobuf: strip comments, collapse whitespace."""
    # Remove block comments /* ... */
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    lines = []
    for line in text.splitlines():
        # Remove single-line comments (// ...)
        comment_pos = _find_proto_comment(line)
        if comment_pos is not None:
            line = line[:comment_pos]
        line = line.rstrip()
        if not line.strip():
            continue
        # Collapse internal whitespace
        line = re.sub(r"[ \t]+", " ", line)
        lines.append(line.strip())
    return "\n".join(lines) + "\n"


def _find_proto_comment(line: str) -> int | None:
    """Find position of // comment in protobuf line (not inside strings)."""
    in_string = False
    escape = False
    i = 0
    while i < len(line):
        ch = line[i]
        if escape:
            escape = False
            i += 1
            continue
        if ch == "\\":
            escape = True
            i += 1
            continue
        if ch == '"':
            in_string = not in_string
        elif ch == "/" and not in_string and i + 1 < len(line) and line[i + 1] == "/":
            return i
        i += 1
    return None


# Format dispatch
MINIFIERS = {
    "openapi": minify_yaml,
    "asyncapi": minify_yaml,
    "graphql": minify_graphql,
    "postman": minify_json,
    "protobuf": minify_protobuf,
}


def minify(text: str, format: str) -> str:
    """Minify a spec string based on its format.

    Args:
        text: Raw spec content.
        format: One of openapi, asyncapi, graphql, postman, protobuf.

    Returns:
        Minified spec string.
    """
    fn = MINIFIERS.get(format)
    if fn is None:
        raise ValueError(f"Unknown format for minification: {format}")
    return fn(text)


def minify_file(src: str | Path, dst: str | Path, format: str) -> int:
    """Minify a spec file and write the result.

    Returns:
        Size of minified output in bytes.
    """
    src, dst = Path(src), Path(dst)
    text = src.read_text(encoding="utf-8")
    result = minify(text, format)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(result, encoding="utf-8")
    return len(result.encode("utf-8"))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python minifier.py <format> <input-file> [output-file]")
        sys.exit(1)
    fmt = sys.argv[1]
    src = Path(sys.argv[2])
    text = src.read_text(encoding="utf-8")
    result = minify(text, fmt)
    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text(result, encoding="utf-8")
    else:
        print(result)
