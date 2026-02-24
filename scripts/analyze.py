#!/usr/bin/env python3
"""
Analyze benchmark results and generate reports.

Usage:
  python scripts/analyze.py <batch_id>              # analyze a batch
  python scripts/analyze.py <batch_id> --format csv  # export CSV
  python scripts/analyze.py <batch_id> --charts      # generate charts
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_batch_results(batch_id: str) -> list[dict]:
    """Load all run results from a batch."""
    batch_dir = PROJECT_ROOT / "results" / "runs" / batch_id
    if not batch_dir.exists():
        print(f"Batch not found: {batch_dir}")
        sys.exit(1)

    results = []
    for f in sorted(batch_dir.glob("*.json")):
        if f.name == "manifest.json":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(data)
        except (json.JSONDecodeError, KeyError):
            pass
    return results


def tier_summary(results: list[dict]) -> dict:
    """Aggregate scores by compression tier."""
    by_tier = defaultdict(list)
    for r in results:
        tier = r.get("tier", "unknown")
        score = r.get("score", {}).get("total", 0)
        by_tier[tier].append(score)

    summary = {}
    for tier, scores in sorted(by_tier.items()):
        n = len(scores)
        avg = sum(scores) / n if n else 0
        summary[tier] = {
            "count": n,
            "avg_score": round(avg, 3),
            "min_score": round(min(scores), 3) if scores else 0,
            "max_score": round(max(scores), 3) if scores else 0,
            "success_rate": round(sum(1 for s in scores if s >= 0.7) / n, 3) if n else 0,
        }
    return summary


def format_summary(results: list[dict]) -> dict:
    """Aggregate scores by spec format."""
    by_format = defaultdict(list)
    for r in results:
        fmt = r.get("format", "unknown")
        score = r.get("score", {}).get("total", 0)
        by_format[fmt].append(score)

    summary = {}
    for fmt, scores in sorted(by_format.items()):
        n = len(scores)
        avg = sum(scores) / n if n else 0
        summary[fmt] = {
            "count": n,
            "avg_score": round(avg, 3),
        }
    return summary


def size_class_summary(results: list[dict]) -> dict:
    """Aggregate scores by spec size class."""
    by_size = defaultdict(lambda: defaultdict(list))
    for r in results:
        size = r.get("static", {}).get("doc_bytes", 0)
        if size < 50000:
            cls = "small"
        elif size < 500000:
            cls = "medium"
        else:
            cls = "large"
        tier = r.get("tier", "unknown")
        score = r.get("score", {}).get("total", 0)
        by_size[cls][tier].append(score)

    summary = {}
    for cls in ["small", "medium", "large"]:
        summary[cls] = {}
        for tier, scores in by_size[cls].items():
            n = len(scores)
            summary[cls][tier] = {
                "count": n,
                "avg_score": round(sum(scores) / n, 3) if n else 0,
            }
    return summary


def compression_analysis(results: list[dict]) -> dict:
    """Analyze token savings vs score tradeoff."""
    by_spec_tier = defaultdict(dict)
    for r in results:
        spec = r.get("spec_id", "unknown")
        tier = r.get("tier", "unknown")
        by_spec_tier[spec][tier] = {
            "score": r.get("score", {}).get("total", 0),
            "tokens": r.get("static", {}).get("doc_tokens", 0),
            "bytes": r.get("static", {}).get("doc_bytes", 0),
        }

    analysis = {}
    for spec, tiers in by_spec_tier.items():
        pretty = tiers.get("pretty", {})
        if not pretty:
            continue
        analysis[spec] = {}
        for tier_name, data in tiers.items():
            if tier_name == "pretty":
                continue
            token_savings = 0
            if pretty.get("tokens"):
                token_savings = round(1 - data["tokens"] / pretty["tokens"], 3)
            score_delta = round(data["score"] - pretty["score"], 3)
            analysis[spec][tier_name] = {
                "token_savings": token_savings,
                "score_delta": score_delta,
                "score": data["score"],
            }
    return analysis


def print_report(results: list[dict]):
    """Print a human-readable analysis report."""
    print(f"{'='*60}")
    print(f"  LAP Benchmark Analysis - {len(results)} runs")
    print(f"{'='*60}")
    print()

    # Tier summary
    tier_data = tier_summary(results)
    print("TIER COMPARISON:")
    print(f"  {'Tier':<15} {'N':>5} {'Avg':>7} {'Min':>7} {'Max':>7} {'Pass':>7}")
    print(f"  {'-'*50}")
    for tier, data in tier_data.items():
        print(
            f"  {tier:<15} {data['count']:>5} "
            f"{data['avg_score']:>7.3f} {data['min_score']:>7.3f} "
            f"{data['max_score']:>7.3f} {data['success_rate']:>6.1%}"
        )
    print()

    # Format summary
    fmt_data = format_summary(results)
    print("FORMAT BREAKDOWN:")
    print(f"  {'Format':<15} {'N':>5} {'Avg':>7}")
    print(f"  {'-'*30}")
    for fmt, data in fmt_data.items():
        print(f"  {fmt:<15} {data['count']:>5} {data['avg_score']:>7.3f}")
    print()

    # Size class
    size_data = size_class_summary(results)
    print("SIZE CLASS x TIER:")
    for cls in ["small", "medium", "large"]:
        if cls not in size_data or not size_data[cls]:
            continue
        tiers = size_data[cls]
        tier_strs = [f"{t}={d['avg_score']:.3f}(n={d['count']})" for t, d in tiers.items()]
        print(f"  {cls:<8}: {', '.join(tier_strs)}")
    print()


def export_csv(results: list[dict], output_path: Path):
    """Export results to CSV."""
    fieldnames = [
        "run_id", "spec_id", "format", "tier", "task_id",
        "score_total", "score_endpoint", "score_params", "score_code",
        "doc_bytes", "doc_tokens", "wall_time_s", "status",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "run_id": r.get("run_id"),
                "spec_id": r.get("spec_id"),
                "format": r.get("format"),
                "tier": r.get("tier"),
                "task_id": r.get("task_id"),
                "score_total": r.get("score", {}).get("total", 0),
                "score_endpoint": r.get("score", {}).get("endpoint", 0),
                "score_params": r.get("score", {}).get("params", 0),
                "score_code": r.get("score", {}).get("code", 0),
                "doc_bytes": r.get("static", {}).get("doc_bytes", 0),
                "doc_tokens": r.get("static", {}).get("doc_tokens", 0),
                "wall_time_s": r.get("execution", {}).get("wall_time_s", 0),
                "status": r.get("execution", {}).get("status", "unknown"),
            })
    print(f"Exported {len(results)} results to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Analyze benchmark results")
    parser.add_argument("batch_id", type=str, help="Batch ID to analyze")
    parser.add_argument("--format", type=str, choices=["text", "csv", "json"], default="text")
    parser.add_argument("--charts", action="store_true", help="Generate charts (requires matplotlib)")
    args = parser.parse_args()

    results = load_batch_results(args.batch_id)
    if not results:
        print("No results found.")
        sys.exit(1)

    if args.format == "csv":
        output_path = PROJECT_ROOT / "results" / "analysis" / f"{args.batch_id}.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        export_csv(results, output_path)
    elif args.format == "json":
        analysis = {
            "batch_id": args.batch_id,
            "total_runs": len(results),
            "tier_summary": tier_summary(results),
            "format_summary": format_summary(results),
            "size_class_summary": size_class_summary(results),
            "compression_analysis": compression_analysis(results),
        }
        output_path = PROJECT_ROOT / "results" / "analysis" / f"{args.batch_id}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2)
        print(f"Exported analysis to {output_path}")
    else:
        print_report(results)


if __name__ == "__main__":
    main()
