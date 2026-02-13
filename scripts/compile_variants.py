#!/usr/bin/env python3
"""
Generate all 4 compression tiers for every spec in the registry.

Tiers:
  pretty    - Original spec, properly formatted (copy from sources/)
  minified  - Whitespace-stripped, comments removed
  standard  - LAP standard (full descriptions)
  lean      - LAP lean (types only, no descriptions)

Usage:
  python scripts/compile_variants.py               # compile all
  python scripts/compile_variants.py --spec stripe  # single spec
  python scripts/compile_variants.py --validate     # check outputs parse
  python scripts/compile_variants.py --dry-run      # show what would be compiled
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

# Force UTF-8 for Path.read_text() on Windows (LAP compiler uses it without encoding arg)
_original_read_text = Path.read_text
def _utf8_read_text(self, encoding=None, errors=None):
    if encoding is None:
        encoding = "utf-8"
    return _original_read_text(self, encoding=encoding, errors=errors)
Path.read_text = _utf8_read_text

# Add project root + LAP core to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
# LAP core: sibling directory to this project (works on Windows + macOS)
_lap_core = PROJECT_ROOT.parent / "lap"
if not _lap_core.exists():
    # Fallback: check common locations
    for candidate in [Path.home() / "LAP" / "lap", Path("/LAP/lap")]:
        if candidate.exists():
            _lap_core = candidate
            break
sys.path.insert(0, str(_lap_core))

import yaml

from harness.minifier import minify_file, minify
from harness.metrics import static_metrics

# Extension map per format (for pretty/minified output)
EXT_MAP = {
    "openapi": ".yaml",
    "asyncapi": ".yaml",
    "graphql": ".graphql",
    "postman": ".json",
    "protobuf": ".proto",
}


def load_registry() -> dict:
    reg_path = PROJECT_ROOT / "registry" / "registry.yaml"
    with open(reg_path, encoding="utf-8") as f:
        return yaml.safe_load(f).get("specs", {})


def compile_spec_tiers(spec_id: str, meta: dict, compiled_dir: Path, dry_run: bool = False):
    """Compile all 4 tiers for a single spec."""
    fmt = meta["format"]
    source_path = PROJECT_ROOT / meta["source_file"]
    ext = EXT_MAP.get(fmt, ".txt")

    out_dir = compiled_dir / fmt / spec_id
    out_dir.mkdir(parents=True, exist_ok=True)

    pretty_path = out_dir / f"pretty{ext}"
    minified_path = out_dir / f"minified{ext}"
    standard_path = out_dir / "standard.lap"
    lean_path = out_dir / "lean.lap"

    if not source_path.exists():
        print(f"  SKIP {spec_id}: source not found ({source_path})")
        return None

    if dry_run:
        print(f"  {spec_id} ({fmt}): {source_path.name} -> {out_dir.relative_to(PROJECT_ROOT)}/")
        return None

    results = {"spec_id": spec_id, "format": fmt, "tiers": {}}

    # 1. Pretty: copy source as-is
    shutil.copy2(source_path, pretty_path)
    results["tiers"]["pretty"] = static_metrics(pretty_path)
    pretty_bytes = results["tiers"]["pretty"]["doc_bytes"]

    # 2. Minified: format-aware whitespace stripping
    try:
        minify_file(source_path, minified_path, fmt)
        m = static_metrics(minified_path)
        m["compression_ratio"] = round(pretty_bytes / m["doc_bytes"], 2) if m["doc_bytes"] else 0
        results["tiers"]["minified"] = m
    except Exception as e:
        print(f"  WARN {spec_id}/minified: {e}")
        results["tiers"]["minified"] = {"error": str(e)}

    # 3. LAP Standard
    try:
        from core.compilers import compile as compile_spec
        result_obj = compile_spec(str(source_path), format=fmt)
        if isinstance(result_obj, list):
            lap_text = "\n---\n\n".join(s.to_lap(lean=False) for s in result_obj)
        else:
            lap_text = result_obj.to_lap(lean=False)
        standard_path.write_text(lap_text, encoding="utf-8")
        m = static_metrics(standard_path)
        m["compression_ratio"] = round(pretty_bytes / m["doc_bytes"], 2) if m["doc_bytes"] else 0
        results["tiers"]["standard"] = m
    except Exception as e:
        print(f"  WARN {spec_id}/standard: {e}")
        results["tiers"]["standard"] = {"error": str(e)}

    # 4. LAP Lean
    try:
        from core.compilers import compile as compile_spec
        result_obj = compile_spec(str(source_path), format=fmt)
        if isinstance(result_obj, list):
            lap_text = "\n---\n\n".join(s.to_lap(lean=True) for s in result_obj)
        else:
            lap_text = result_obj.to_lap(lean=True)
        lean_path.write_text(lap_text, encoding="utf-8")
        m = static_metrics(lean_path)
        m["compression_ratio"] = round(pretty_bytes / m["doc_bytes"], 2) if m["doc_bytes"] else 0
        results["tiers"]["lean"] = m
    except Exception as e:
        print(f"  WARN {spec_id}/lean: {e}")
        results["tiers"]["lean"] = {"error": str(e)}

    # Summary line
    tiers = results["tiers"]
    parts = []
    for tier_name in ["pretty", "minified", "standard", "lean"]:
        t = tiers.get(tier_name, {})
        if "error" in t:
            parts.append(f"{tier_name}=ERR")
        else:
            b = t.get("doc_bytes", 0)
            r = t.get("compression_ratio", 1.0)
            parts.append(f"{tier_name}={b:,}B({r:.1f}x)")
    print(f"  OK {spec_id}: {' | '.join(parts)}")
    return results


def validate_outputs(compiled_dir: Path, registry: dict):
    """Validate that compiled outputs parse correctly."""
    import json

    ok = 0
    fail = 0

    for spec_id, meta in sorted(registry.items()):
        fmt = meta["format"]
        ext = EXT_MAP.get(fmt, ".txt")
        out_dir = compiled_dir / fmt / spec_id

        # Check pretty and minified parse
        for tier in ["pretty", "minified"]:
            path = out_dir / f"{tier}{ext}"
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8")
                if ext == ".json":
                    json.loads(text)
                elif ext in (".yaml", ".yml"):
                    yaml.safe_load(text)
                # GraphQL and Protobuf: just check non-empty
                if len(text.strip()) == 0:
                    raise ValueError("Empty output")
                ok += 1
            except Exception as e:
                print(f"  FAIL {spec_id}/{tier}: {e}")
                fail += 1

        # Check LAP outputs exist and are non-empty
        for tier in ["standard", "lean"]:
            path = out_dir / f"{tier}.lap"
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            if len(text.strip()) == 0:
                print(f"  FAIL {spec_id}/{tier}: empty LAP output")
                fail += 1
            else:
                ok += 1

    print(f"\nValidation: {ok} OK, {fail} FAILED")
    return fail == 0


def main():
    parser = argparse.ArgumentParser(description="Compile benchmark spec variants")
    parser.add_argument("--spec", type=str, help="Compile single spec by ID")
    parser.add_argument("--validate", action="store_true", help="Validate compiled outputs")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be compiled")
    parser.add_argument("--format", type=str, help="Filter by format (openapi, asyncapi, ...)")
    args = parser.parse_args()

    registry = load_registry()
    compiled_dir = PROJECT_ROOT / "compiled"

    if args.validate:
        ok = validate_outputs(compiled_dir, registry)
        sys.exit(0 if ok else 1)

    # Filter specs
    if args.spec:
        if args.spec not in registry:
            print(f"Unknown spec: {args.spec}")
            print(f"Available: {', '.join(sorted(registry.keys()))}")
            sys.exit(1)
        specs = {args.spec: registry[args.spec]}
    elif args.format:
        specs = {k: v for k, v in registry.items() if v["format"] == args.format}
        if not specs:
            print(f"No specs with format: {args.format}")
            sys.exit(1)
    else:
        specs = registry

    print(f"Compiling {len(specs)} specs x 4 tiers = {len(specs) * 4} variants")
    print()

    all_results = []
    for spec_id in sorted(specs.keys()):
        result = compile_spec_tiers(spec_id, specs[spec_id], compiled_dir, dry_run=args.dry_run)
        if result:
            all_results.append(result)

    if not args.dry_run:
        print(f"\nDone. {len(all_results)} specs compiled to {compiled_dir}")


if __name__ == "__main__":
    main()
