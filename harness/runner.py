#!/usr/bin/env python3
"""
Batch orchestrator for LAP Benchmark v2.

Manages execution of benchmark runs with:
  - Prioritization (large specs first)
  - Checkpointing (resume on failure)
  - Concurrency control
  - Integration with scorer and metrics

Usage:
  python -m harness.runner --pilot              # 6 specs, 2 tasks, all tiers
  python -m harness.runner --full               # all specs, all tasks, all tiers
  python -m harness.runner --spec stripe        # single spec
  python -m harness.runner --resume <batch_id>  # resume interrupted batch
  python -m harness.runner --dry-run            # show manifest only
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from harness.executor import execute_run, save_run_result, copy_recording, generate_run_id
from harness.scorer import score_run
from harness.metrics import static_metrics


def load_config() -> dict:
    config_path = PROJECT_ROOT / "harness" / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_registry() -> dict:
    reg_path = PROJECT_ROOT / "registry" / "registry.yaml"
    with open(reg_path, encoding="utf-8") as f:
        return yaml.safe_load(f).get("specs", {})


def load_manifest(spec_id: str, fmt: str) -> dict | None:
    manifest_path = PROJECT_ROOT / "registry" / "manifests" / fmt / f"{spec_id}.yaml"
    if not manifest_path.exists():
        return None
    with open(manifest_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_compiled_path(spec_id: str, fmt: str, tier: str) -> Path | None:
    """Get the path to a compiled doc variant."""
    filename = get_tier_filename(fmt, tier)
    if not filename:
        return None
    path = PROJECT_ROOT / "compiled" / fmt / spec_id / filename
    return path if path.exists() else None


def get_tier_filename(fmt: str, tier: str) -> str | None:
    """Get the filename for a given format + tier combination."""
    ext_map = {
        "openapi": ".yaml", "asyncapi": ".yaml",
        "graphql": ".graphql", "postman": ".json", "protobuf": ".proto",
    }
    tier_map = {
        "pretty": f"pretty{ext_map.get(fmt, '.txt')}",
        "minified": f"minified{ext_map.get(fmt, '.txt')}",
        "lap-standard": "standard.lap",
        "lap-lean": "lean.lap",
    }
    return tier_map.get(tier)


def build_doc_url(config: dict, fmt: str, spec_id: str, tier: str) -> str | None:
    """Construct a GitHub raw URL for a compiled doc variant."""
    gh = config.get("github")
    if not gh:
        return None
    filename = get_tier_filename(fmt, tier)
    if not filename:
        return None
    base = gh["base_url"]
    repo = gh["repo"]
    branch = gh["branch"]
    return f"{base}/{repo}/{branch}/compiled/{fmt}/{spec_id}/{filename}"


SIZE_ORDER = {"large": 0, "medium": 1, "small": 2}


def build_run_manifest(
    registry: dict,
    config: dict,
    spec_filter: str | None = None,
    format_filter: str | None = None,
    tier_filter: str | None = None,
    task_filter: str | None = None,
    pilot: bool = False,
) -> list[dict]:
    """Build ordered list of runs to execute."""
    tiers = config.get("tiers", ["pretty", "minified", "lap-standard", "lap-lean"])
    if tier_filter:
        tiers = [t for t in tiers if t == tier_filter]
    runs = []

    specs = registry
    if spec_filter:
        specs = {k: v for k, v in specs.items() if k == spec_filter}
    if format_filter:
        specs = {k: v for k, v in specs.items() if v["format"] == format_filter}

    # Sort by size (large first)
    sorted_specs = sorted(
        specs.items(),
        key=lambda x: SIZE_ORDER.get(x[1].get("size_class", "small"), 2),
    )

    if pilot:
        # Pick 6 specs: 2 per size class where available
        by_size = {"large": [], "medium": [], "small": []}
        for sid, meta in sorted_specs:
            by_size.setdefault(meta.get("size_class", "small"), []).append((sid, meta))
        pilot_specs = []
        for size in ["large", "medium", "small"]:
            pilot_specs.extend(by_size.get(size, [])[:2])
        sorted_specs = pilot_specs[:6]

    for spec_id, meta in sorted_specs:
        fmt = meta["format"]
        manifest = load_manifest(spec_id, fmt)
        if not manifest:
            continue

        tasks = manifest.get("tasks", [])
        if task_filter:
            tasks = [t for t in tasks if t["id"] == task_filter]

        for task in tasks:
            for tier in tiers:
                if tier == "none":
                    # No-doc baseline: no compiled doc needed
                    doc_path_str = ""
                    doc_url = None
                else:
                    doc_path = get_compiled_path(spec_id, fmt, tier)
                    if not doc_path:
                        continue
                    doc_path_str = str(doc_path)
                    doc_url = build_doc_url(config, fmt, spec_id, tier)
                run_id = generate_run_id(spec_id, tier, task["id"])
                runs.append({
                    "run_id": run_id,
                    "spec_id": spec_id,
                    "format": fmt,
                    "tier": tier,
                    "task_id": task["id"],
                    "task_description": task["description"],
                    "target_endpoints": task.get("target_endpoints", []),
                    "expected_params": task.get("expected_params", {}),
                    "doc_path": doc_path_str,
                    "doc_url": doc_url,
                    "size_class": meta.get("size_class", "small"),
                })

    return runs


def execute_and_score(run: dict, config: dict, batch_dir: Path, local: bool = False) -> dict:
    """Execute a single run and score the output."""
    model = config.get("model", "claude-sonnet-4-5-20250929")
    timeout = config.get("timeout_seconds", 180)
    allowed_tools = config.get("claude_cli", {}).get("allowed_tools")
    scoring_config = config.get("scoring", {})

    # Get static metrics (skip for no-doc baseline)
    doc_path = Path(run["doc_path"]) if run["doc_path"] else None
    static = static_metrics(doc_path) if doc_path and doc_path.exists() else {}

    # Execute
    result = execute_run(
        spec_id=run["spec_id"],
        tier=run["tier"],
        task_id=run["task_id"],
        task_description=run["task_description"],
        doc_path=doc_path,
        doc_url=run.get("doc_url"),
        model=model,
        timeout=timeout,
        allowed_tools=allowed_tools,
        local=local,
    )

    result["format"] = run["format"]
    result["static"] = static

    # Score
    output_text = result.get("execution", {}).get("output_text", "")
    if output_text and result["execution"].get("status") == "completed":
        weights = {
            "endpoint": scoring_config.get("endpoint_weight", 0.6),
            "param": scoring_config.get("param_weight", 0.3),
            "code": scoring_config.get("code_weight", 0.1),
        }
        score = score_run(
            output_text,
            run.get("target_endpoints", []),
            run.get("expected_params", {}),
            weights=weights,
        )
        result["score"] = score
    else:
        result["score"] = {"total": 0.0, "endpoint": 0.0, "params": 0.0, "code": 0.0}

    # Save result
    save_run_result(result, batch_dir)

    # Copy recording
    recordings_dir = batch_dir / "recordings"
    copy_recording(result, recordings_dir)

    return result


def load_checkpoint(batch_dir: Path) -> set:
    """Load completed run IDs from a batch directory."""
    completed = set()
    for f in batch_dir.glob("*.json"):
        if f.name == "manifest.json":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("execution", {}).get("status") in ("completed", "error", "timeout"):
                completed.add(data.get("run_id"))
        except (json.JSONDecodeError, KeyError):
            pass
    return completed


def main():
    parser = argparse.ArgumentParser(description="LAP Benchmark v2 Runner")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pilot", action="store_true", help="6 specs x 2 tasks x 4 tiers")
    group.add_argument("--full", action="store_true", help="All specs x all tasks x all tiers")
    group.add_argument("--spec", type=str, help="Single spec by ID")
    group.add_argument("--resume", type=str, help="Resume batch by ID")
    parser.add_argument("--dry-run", action="store_true", help="Show manifest only")
    parser.add_argument("--format", type=str, help="Filter by format")
    parser.add_argument("--tier", type=str, help="Filter by tier (pretty, minified, lap-standard, lap-lean)")
    parser.add_argument("--task", type=str, help="Filter by task ID (e.g. t1)")
    parser.add_argument("--concurrency", type=int, help="Override concurrency")
    parser.add_argument("--local", action="store_true", help="Use local file copy instead of URL delivery")
    args = parser.parse_args()

    config = load_config()
    registry = load_registry()

    # Resolve batch directory
    if args.resume:
        batch_dir = PROJECT_ROOT / "results" / "runs" / args.resume
        if not batch_dir.exists():
            print(f"Batch not found: {batch_dir}")
            sys.exit(1)
        batch_id = args.resume
    else:
        batch_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        batch_dir = PROJECT_ROOT / "results" / "runs" / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)

    # Build run manifest
    runs = build_run_manifest(
        registry, config,
        spec_filter=args.spec,
        format_filter=args.format,
        tier_filter=args.tier,
        task_filter=args.task,
        pilot=args.pilot,
    )

    # Filter out already completed runs if resuming
    completed_ids = load_checkpoint(batch_dir) if args.resume else set()
    pending_runs = [r for r in runs if r["run_id"] not in completed_ids]

    # Save manifest
    manifest = {
        "batch_id": batch_id,
        "created": datetime.now(timezone.utc).isoformat(),
        "model": config.get("model"),
        "total_runs": len(runs),
        "pending_runs": len(pending_runs),
        "completed_runs": len(completed_ids),
    }
    manifest_path = batch_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Batch: {batch_id}")
    print(f"Total runs: {len(runs)}")
    print(f"Pending: {len(pending_runs)}")
    print(f"Already completed: {len(completed_ids)}")
    print()

    if args.dry_run:
        for r in pending_runs:
            print(f"  [{r['run_id']}] {r['spec_id']}:{r['tier']}:{r['task_id']} ({r['size_class']})")
        return

    if not pending_runs:
        print("Nothing to run.")
        return

    # Execute runs
    concurrency = args.concurrency or config.get("concurrency", 3)
    print(f"Running with concurrency={concurrency}")
    print()

    completed = 0
    failed = 0
    start_time = time.time()

    use_local = args.local

    if concurrency == 1:
        for run in pending_runs:
            print(f"  [{completed+1}/{len(pending_runs)}] {run['spec_id']}:{run['tier']}:{run['task_id']}...", end=" ", flush=True)
            result = execute_and_score(run, config, batch_dir, local=use_local)
            status = result["execution"]["status"]
            score = result.get("score", {}).get("total", 0)
            print(f"{status} (score={score:.2f})")
            completed += 1
            if status != "completed":
                failed += 1
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {
                pool.submit(execute_and_score, run, config, batch_dir, use_local): run
                for run in pending_runs
            }
            for future in as_completed(futures):
                run = futures[future]
                try:
                    result = future.result()
                    status = result["execution"]["status"]
                    score = result.get("score", {}).get("total", 0)
                    completed += 1
                    print(f"  [{completed}/{len(pending_runs)}] {run['spec_id']}:{run['tier']}:{run['task_id']} -> {status} (score={score:.2f})")
                    if status != "completed":
                        failed += 1
                except Exception as e:
                    completed += 1
                    failed += 1
                    print(f"  [{completed}/{len(pending_runs)}] {run['spec_id']}:{run['tier']}:{run['task_id']} -> EXCEPTION: {e}")

    elapsed = time.time() - start_time
    print(f"\nDone in {elapsed:.1f}s. Completed: {completed}, Failed: {failed}")
    print(f"Results: {batch_dir}")


if __name__ == "__main__":
    main()
