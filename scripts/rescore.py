#!/usr/bin/env python3
"""Re-score existing benchmark runs with updated scorer logic.

This script re-scores all runs in a batch directory without re-executing agents.
It's useful after making fixes to the scoring algorithm to retroactively apply
the new scoring logic to existing run results.

Usage:
    python scripts/rescore.py 20260213_003225
    python scripts/rescore.py 20260213_003225 --regenerate-pilot
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

# Add harness to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "harness"))

from scorer import score_run


def load_registry():
    """Load the spec registry to map spec_id -> format."""
    registry_path = PROJECT_ROOT / "registry" / "registry.yaml"
    with open(registry_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {spec_id: meta["format"] for spec_id, meta in data["specs"].items()}


def load_manifest(format_name, spec_id):
    """Load the manifest file for a spec to get tasks."""
    manifest_path = PROJECT_ROOT / "registry" / "manifests" / format_name / f"{spec_id}.yaml"
    with open(manifest_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def rescore_batch(batch_id, verbose=True):
    """Re-score all runs in a batch directory.

    Args:
        batch_id: Batch directory name (e.g., "20260213_003225")
        verbose: Print progress messages

    Returns:
        List of (run_file, old_score, new_score) tuples
    """
    batch_dir = PROJECT_ROOT / "results" / "runs" / batch_id
    if not batch_dir.exists():
        print(f"Error: Batch directory not found: {batch_dir}")
        sys.exit(1)

    registry = load_registry()
    results = []

    # Process all JSON files except manifest.json
    run_files = sorted([f for f in batch_dir.glob("*.json") if f.name != "manifest.json"])

    if verbose:
        print(f"Re-scoring {len(run_files)} runs in batch {batch_id}...")

    for run_file in run_files:
        # Load run data
        with open(run_file, encoding="utf-8") as f:
            run_data = json.load(f)

        spec_id = run_data["spec_id"]
        task_id = run_data["task_id"]
        format_name = run_data.get("format") or registry.get(spec_id)

        if not format_name:
            print(f"Warning: No format found for spec {spec_id}, skipping {run_file.name}")
            continue

        # Load manifest to get expected endpoints/params
        try:
            manifest = load_manifest(format_name, spec_id)
        except FileNotFoundError:
            print(f"Warning: Manifest not found for {format_name}/{spec_id}, skipping {run_file.name}")
            continue

        # Find the matching task
        task = next((t for t in manifest["tasks"] if t["id"] == task_id), None)
        if not task:
            print(f"Warning: Task {task_id} not found in manifest for {spec_id}, skipping {run_file.name}")
            continue

        target_endpoints = task.get("target_endpoints", [])
        expected_params = task.get("expected_params", {})

        # Skip runs that failed or timed out (no output_text)
        output_text = run_data["execution"].get("output_text")
        if not output_text:
            if verbose:
                print(f"  {run_file.name}: skipped (no output)")
            continue

        # Re-score using the updated scorer
        old_score = run_data["score"]
        new_score = score_run(output_text, target_endpoints, expected_params)

        # Update the score in the run data
        run_data["score"] = new_score

        # Save the updated run file
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(run_data, f, indent=2)

        results.append((run_file.name, old_score, new_score))

        if verbose:
            old_total = old_score["total"]
            new_total = new_score["total"]
            delta = new_total - old_total
            delta_str = f"{delta:+.3f}" if delta != 0 else " 0.000"
            print(f"  {run_file.name}: {old_total:.3f} -> {new_total:.3f} ({delta_str})")

    return results


def _run_to_record(run: dict) -> dict:
    """Convert a run result dict to a pilot_data record."""
    execution = run["execution"]
    score = run.get("score", {})
    return {
        "spec": run["spec_id"],
        "tier": run["tier"],
        "task": run["task_id"],
        "format": run["format"],
        "status": execution["status"],
        "score": score.get("total", 0),
        "ep": score.get("endpoint", 0),
        "par": score.get("params", 0),
        "code": score.get("code", 0),
        "time": execution.get("wall_time_s", 0),
        "cost": execution.get("cost_usd", 0),
        "input_tokens": execution.get("input_tokens", 0),
        "output_tokens": execution.get("output_tokens", 0),
        "cache_create": execution.get("cache_creation_tokens", 0),
        "cache_read": execution.get("cache_read_tokens", 0),
        "total_tokens": execution.get("total_tokens", 0),
        "num_turns": execution.get("num_turns", 0),
        "doc_tokens": run.get("static", {}).get("doc_tokens", 0),
        "doc_bytes": run.get("static", {}).get("doc_bytes", 0),
    }


def regenerate_pilot_data(batch_id=None):
    """Regenerate results/pilot_data.json from ALL batches.

    Scans all batch directories and takes the latest completed run
    for each (spec, tier, task) combination.
    """
    runs_dir = PROJECT_ROOT / "results" / "runs"
    best = {}  # (spec, tier, task) -> (batch_id, record)

    batch_dirs = sorted(runs_dir.iterdir()) if not batch_id else [runs_dir / batch_id]

    for batch_dir in batch_dirs:
        if not batch_dir.is_dir():
            continue
        for run_file in batch_dir.glob("*.json"):
            if run_file.name == "manifest.json":
                continue
            try:
                with open(run_file, encoding="utf-8") as f:
                    run = json.load(f)
            except (json.JSONDecodeError, KeyError):
                continue

            key = (run["spec_id"], run["tier"], run["task_id"])
            status = run.get("execution", {}).get("status")

            # Prefer completed > timeout > error
            record = _run_to_record(run)
            existing = best.get(key)

            if not existing:
                best[key] = (batch_dir.name, record)
            else:
                old_status = existing[1]["status"]
                # Replace if new run is completed and old wasn't, or both same status and newer batch
                if status == "completed" and old_status != "completed":
                    best[key] = (batch_dir.name, record)
                elif status == old_status and batch_dir.name > existing[0]:
                    best[key] = (batch_dir.name, record)

    pilot_data = [record for _, record in sorted(best.values(), key=lambda x: (x[1]["spec"], x[1]["task"], x[1]["tier"]))]

    output_path = PROJECT_ROOT / "results" / "pilot_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pilot_data, f, indent=2)

    completed = sum(1 for r in pilot_data if r["status"] == "completed")
    print(f"\nRegenerated {output_path} with {len(pilot_data)} records ({completed} completed)")


def main():
    parser = argparse.ArgumentParser(description="Re-score benchmark runs with updated scorer")
    parser.add_argument("batch_id", help="Batch directory name (e.g., 20260213_003225)")
    parser.add_argument(
        "--regenerate-pilot",
        action="store_true",
        help="Regenerate results/pilot_data.json after re-scoring"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file progress output"
    )

    args = parser.parse_args()

    # Re-score all runs
    results = rescore_batch(args.batch_id, verbose=not args.quiet)

    # Print summary
    if results:
        print(f"\n{'='*60}")
        print(f"Re-scored {len(results)} runs")

        # Calculate overall delta
        total_delta = sum(new["total"] - old["total"] for _, old, new in results)
        avg_delta = total_delta / len(results)
        print(f"Average score change: {avg_delta:+.3f}")

        # Show biggest changes
        by_delta = sorted(results, key=lambda x: abs(x[2]["total"] - x[1]["total"]), reverse=True)
        print(f"\nBiggest changes:")
        for run_file, old, new in by_delta[:5]:
            delta = new["total"] - old["total"]
            print(f"  {run_file}: {old['total']:.3f} -> {new['total']:.3f} ({delta:+.3f})")

    # Optionally regenerate pilot data (scans ALL batches)
    if args.regenerate_pilot:
        regenerate_pilot_data()


if __name__ == "__main__":
    main()
