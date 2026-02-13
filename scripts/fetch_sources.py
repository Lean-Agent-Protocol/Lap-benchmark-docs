#!/usr/bin/env python3
"""
Download spec source files from GitHub URLs listed in the registry.

Usage:
  python scripts/fetch_sources.py               # fetch all with github_url
  python scripts/fetch_sources.py --spec stripe  # fetch single spec
  python scripts/fetch_sources.py --dry-run      # show what would be fetched
"""

import argparse
import sys
import urllib.request
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_registry() -> dict:
    reg_path = PROJECT_ROOT / "registry" / "registry.yaml"
    with open(reg_path, encoding="utf-8") as f:
        return yaml.safe_load(f).get("specs", {})


def fetch_spec(spec_id: str, meta: dict, force: bool = False) -> bool:
    """Download a spec source file from its github_url.

    Returns True if file was downloaded, False if skipped.
    """
    url = meta.get("github_url")
    if not url:
        return False

    dest = PROJECT_ROOT / meta["source_file"]
    if dest.exists() and not force:
        print(f"  SKIP {spec_id}: already exists at {dest}")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        print(f"  FETCH {spec_id}: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "LAP-Benchmark/2.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        dest.write_bytes(data)
        print(f"    -> {dest} ({len(data):,} bytes)")
        return True
    except Exception as e:
        print(f"  ERROR {spec_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Fetch spec source files")
    parser.add_argument("--spec", type=str, help="Fetch single spec by ID")
    parser.add_argument("--force", action="store_true", help="Re-download even if exists")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fetched")
    args = parser.parse_args()

    registry = load_registry()

    if args.spec:
        if args.spec not in registry:
            print(f"Unknown spec: {args.spec}")
            sys.exit(1)
        specs = {args.spec: registry[args.spec]}
    else:
        specs = registry

    # Filter to specs with github_url
    fetchable = {k: v for k, v in specs.items() if v.get("github_url")}
    local_only = {k: v for k, v in specs.items() if not v.get("github_url")}

    print(f"Fetchable: {len(fetchable)} specs")
    if local_only:
        print(f"Local only (no URL): {len(local_only)} specs")
    print()

    if args.dry_run:
        for spec_id, meta in sorted(fetchable.items()):
            dest = PROJECT_ROOT / meta["source_file"]
            exists = "EXISTS" if dest.exists() else "MISSING"
            print(f"  [{exists}] {spec_id}: {meta['github_url']}")
        return

    fetched = 0
    for spec_id, meta in sorted(fetchable.items()):
        if fetch_spec(spec_id, meta, force=args.force):
            fetched += 1

    print(f"\nFetched {fetched} specs")


if __name__ == "__main__":
    main()
