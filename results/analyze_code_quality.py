#!/usr/bin/env python3
"""Analyze code quality scores from benchmark run results."""

import json
import os
import glob
import re

run_dir = os.path.join(os.path.dirname(__file__), "runs", "20260213_003225")
files = glob.glob(os.path.join(run_dir, "*.json"))

# Find cases where endpoints_in_code=0 but has_code=True
interesting = []
for f in sorted(files):
    fname = os.path.basename(f)
    if fname == "manifest.json":
        continue
    with open(f, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    score = data.get("score", {})
    code_detail = score.get("code_detail", {})

    if code_detail.get("has_code", False) and code_detail.get("endpoints_in_code", 0) == 0:
        interesting.append({
            "file": fname,
            "spec_id": data.get("spec_id"),
            "tier": data.get("tier"),
            "task_id": data.get("task_id"),
            "output_text": data.get("output_text", ""),
            "target_endpoints": data.get("task", {}).get("target_endpoints", []),
            "expected_params": data.get("task", {}).get("expected_params", {}),
        })

print(f"Found {len(interesting)} cases where has_code=True but endpoints_in_code=0")
print()

# Show details for 3 different spec+task cases
seen_specs = set()
shown = 0
for r in interesting:
    key = f"{r['spec_id']}_{r['task_id']}"
    if key in seen_specs:
        continue
    seen_specs.add(key)
    if shown >= 4:
        break
    shown += 1

    print("=" * 100)
    print(f"CASE {shown}: {r['spec_id']} / {r['task_id']} / {r['tier']}")
    print(f"File: {r['file']}")
    print(f"Target endpoints: {r['target_endpoints']}")
    print()

    # Extract python code blocks
    code_blocks = re.findall(r"```(?:python|py)\n(.*?)```", r["output_text"], re.DOTALL | re.IGNORECASE)
    if code_blocks:
        for i, block in enumerate(code_blocks):
            print(f"--- Python code block {i+1} ---")
            print(block[:2000])
            print()
    else:
        print("NO Python code blocks found")
        # Show what code blocks exist
        all_blocks = re.findall(r"```(\w*)\n(.*?)```", r["output_text"], re.DOTALL)
        if all_blocks:
            for lang, block in all_blocks[:3]:
                print(f"--- Code block (lang={repr(lang)}) ---")
                print(block[:1000])
                print()
        else:
            print("NO code blocks at all!")
    print()


# Now also find cases where endpoints_in_code > 0 to show what the scorer DID match
print("\n" + "=" * 100)
print("CASES WHERE endpoints_in_code > 0 (scorer succeeded)")
print("=" * 100)

success = []
for f in sorted(files):
    fname = os.path.basename(f)
    if fname == "manifest.json":
        continue
    with open(f, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    score = data.get("score", {})
    code_detail = score.get("code_detail", {})

    if code_detail.get("has_code", False) and code_detail.get("endpoints_in_code", 0) > 0:
        success.append({
            "file": fname,
            "spec_id": data.get("spec_id"),
            "tier": data.get("tier"),
            "task_id": data.get("task_id"),
            "output_text": data.get("output_text", ""),
            "target_endpoints": data.get("task", {}).get("target_endpoints", []),
            "ep_score": code_detail.get("endpoints_in_code", 0),
        })

print(f"Found {len(success)} cases where endpoints_in_code > 0")
for r in success[:2]:
    print(f"\n--- {r['spec_id']} / {r['task_id']} / {r['tier']} (ep_score={r['ep_score']}) ---")
    print(f"Target endpoints: {r['target_endpoints']}")
    code_blocks = re.findall(r"```(?:python|py)\n(.*?)```", r["output_text"], re.DOTALL | re.IGNORECASE)
    if code_blocks:
        for i, block in enumerate(code_blocks):
            print(f"Code block {i+1}:")
            print(block[:1500])
    print()
