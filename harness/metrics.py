#!/usr/bin/env python3
"""
Static metrics for benchmark specs -- token counting, size measurement,
compression ratio calculation.
"""

import os
from pathlib import Path

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
except ImportError:
    _enc = None


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken (cl100k_base). Falls back to word-based estimate."""
    if _enc is not None:
        return len(_enc.encode(text))
    # Rough fallback: ~4 chars per token
    return len(text) // 4


def file_bytes(path: str | Path) -> int:
    """Return file size in bytes."""
    return os.path.getsize(path)


def file_tokens(path: str | Path) -> int:
    """Count tokens in a file."""
    text = Path(path).read_text(encoding="utf-8")
    return count_tokens(text)


def compression_ratio(original_bytes: int, compressed_bytes: int) -> float:
    """Calculate compression ratio (original / compressed). Higher = better."""
    if compressed_bytes == 0:
        return 0.0
    return original_bytes / compressed_bytes


def static_metrics(path: str | Path) -> dict:
    """Compute all static metrics for a single doc file.

    Returns:
        {doc_bytes, doc_tokens}
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    return {
        "doc_bytes": len(text.encode("utf-8")),
        "doc_tokens": count_tokens(text),
    }


def compare_tiers(tier_paths: dict[str, Path], pretty_path: Path | None = None) -> dict:
    """Compare metrics across compression tiers.

    Args:
        tier_paths: {tier_name: Path} for each tier.
        pretty_path: Path to the pretty (original) tier for ratio calculation.

    Returns:
        {tier_name: {doc_bytes, doc_tokens, compression_ratio}}
    """
    results = {}
    pretty_bytes = None
    if pretty_path and pretty_path.exists():
        pretty_bytes = file_bytes(pretty_path)

    for tier, path in tier_paths.items():
        if not Path(path).exists():
            results[tier] = {"doc_bytes": 0, "doc_tokens": 0, "compression_ratio": 0.0}
            continue
        m = static_metrics(path)
        if pretty_bytes is not None:
            m["compression_ratio"] = compression_ratio(pretty_bytes, m["doc_bytes"])
        else:
            m["compression_ratio"] = 1.0
        results[tier] = m
    return results
