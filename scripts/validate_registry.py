#!/usr/bin/env python3
"""
Validate the benchmark registry and all task manifests.

Checks:
  - registry.yaml is valid and has required fields per spec
  - Each spec has a source file that exists
  - Each spec has a manifest file with exactly 2 tasks
  - Each task has target_endpoints (2) and expected_params
  - No orphan manifests (manifest without registry entry)
"""

import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "registry" / "registry.yaml"
MANIFESTS_DIR = PROJECT_ROOT / "registry" / "manifests"

VALID_FORMATS = {"openapi", "asyncapi", "graphql", "postman", "protobuf"}
VALID_SIZE_CLASSES = {"small", "medium", "large"}

errors = []
warnings = []


def err(msg: str):
    errors.append(msg)


def warn(msg: str):
    warnings.append(msg)


def validate_manifest(spec_id: str, manifest_path: Path, spec_meta: dict):
    """Validate a single manifest file."""
    if not manifest_path.exists():
        err(f"[{spec_id}] Manifest file missing: {manifest_path}")
        return

    with open(manifest_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        err(f"[{spec_id}] Manifest is not a YAML mapping")
        return

    if data.get("spec_id") != spec_id:
        err(f"[{spec_id}] Manifest spec_id mismatch: expected '{spec_id}', got '{data.get('spec_id')}'")

    tasks = data.get("tasks", [])
    if not isinstance(tasks, list):
        err(f"[{spec_id}] tasks must be a list")
        return

    if len(tasks) != 2:
        err(f"[{spec_id}] Expected exactly 2 tasks, got {len(tasks)}")

    for i, task in enumerate(tasks):
        tid = task.get("id", f"task[{i}]")

        if "description" not in task:
            err(f"[{spec_id}/{tid}] Missing description")

        endpoints = task.get("target_endpoints", [])
        if not isinstance(endpoints, list) or len(endpoints) != 2:
            err(f"[{spec_id}/{tid}] target_endpoints must be a list of exactly 2 items, got {len(endpoints) if isinstance(endpoints, list) else type(endpoints).__name__}")

        params = task.get("expected_params", {})
        if not isinstance(params, dict):
            err(f"[{spec_id}/{tid}] expected_params must be a mapping")
        elif len(params) == 0:
            warn(f"[{spec_id}/{tid}] expected_params is empty")


def main():
    if not REGISTRY_PATH.exists():
        print(f"ERROR: Registry not found at {REGISTRY_PATH}")
        sys.exit(1)

    with open(REGISTRY_PATH, encoding="utf-8") as f:
        registry = yaml.safe_load(f)

    specs = registry.get("specs", {})
    if not specs:
        print("ERROR: No specs found in registry")
        sys.exit(1)

    print(f"Registry: {len(specs)} specs")

    # Validate each spec
    for spec_id, meta in specs.items():
        # Required fields
        fmt = meta.get("format")
        if fmt not in VALID_FORMATS:
            err(f"[{spec_id}] Invalid format: {fmt}")
            continue

        source = meta.get("source_file")
        if not source:
            err(f"[{spec_id}] Missing source_file")
        else:
            source_path = PROJECT_ROOT / source
            if not source_path.exists():
                err(f"[{spec_id}] Source file not found: {source_path}")

        size_class = meta.get("size_class")
        if size_class not in VALID_SIZE_CLASSES:
            err(f"[{spec_id}] Invalid size_class: {size_class}")

        if "domain" not in meta:
            warn(f"[{spec_id}] Missing domain field")

        # Validate manifest
        manifest_path = MANIFESTS_DIR / fmt / f"{spec_id}.yaml"
        validate_manifest(spec_id, manifest_path, meta)

    # Check for orphan manifests
    registered_ids = set(specs.keys())
    for fmt_dir in MANIFESTS_DIR.iterdir():
        if not fmt_dir.is_dir():
            continue
        for manifest_file in fmt_dir.glob("*.yaml"):
            manifest_id = manifest_file.stem
            if manifest_id not in registered_ids:
                warn(f"Orphan manifest: {manifest_file.relative_to(PROJECT_ROOT)} (not in registry)")

    # Report
    print()
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  ! {w}")
        print()

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  X {e}")
        print(f"\nValidation FAILED with {len(errors)} error(s)")
        sys.exit(1)
    else:
        print(f"Validation PASSED ({len(specs)} specs, {len(specs)*2} tasks)")
        sys.exit(0)


if __name__ == "__main__":
    main()
