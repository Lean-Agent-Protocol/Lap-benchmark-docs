#!/usr/bin/env python3
"""Deep-dive into twilio requests-based runs: why ep_in_code=0?"""

import json
import os
import glob
import re
import sys

# Add harness to path for scorer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from harness.scorer import normalize_path, score_code_quality, extract_code_blocks

run_dir = os.path.join(os.path.dirname(__file__), "runs", "20260213_003225")
files = glob.glob(os.path.join(run_dir, "*.json"))

# Build index
index = {}
for f in sorted(files):
    fname = os.path.basename(f)
    if fname == "manifest.json":
        continue
    with open(f, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    key = f"{data.get('spec_id')}_{data.get('task_id')}_{data.get('tier')}"
    index[key] = data

# Case: twilio_t1_pretty (uses requests, ep_in_code=0)
print("=" * 100)
print("DEEP DIVE: twilio_t1_pretty - uses requests library, ep_in_code=0")
print("=" * 100)

data = index["twilio_t1_pretty"]
text = data["execution"]["output_text"]
found_eps = data["score"]["found_endpoints"]

print(f"Found endpoints by scorer: {found_eps}")
print()

code = extract_code_blocks(text)
print(f"Extracted code ({len(code)} chars):")
print(code[:2000])

# What does the scorer look for?
# target_endpoints from found_endpoints = ["POST /2010-04-01/Accounts/{AccountSid}/Messages.json", ...]
# path_stem for POST /2010-04-01/Accounts/{AccountSid}/Messages.json
# = strip {params}: /2010-04-01/Accounts//Messages.json -> strip trailing /: /2010-04-01/Accounts//Messages.json
target_eps = found_eps
print(f"\n\nTarget endpoints used for scoring: {target_eps}")

for ep in target_eps:
    ep_norm = normalize_path(ep)
    parts = ep_norm.split(None, 1)
    if len(parts) != 2:
        print(f"  {ep}: could not split into method+path")
        continue
    method, path = parts
    path_stem = re.sub(r"\{[^}]+\}", "", path).rstrip("/")
    method_lower = method.lower()

    code_lines = [ln for ln in code.split("\n") if not ln.lstrip().startswith("#")]
    code_no_comments = "\n".join(code_lines).lower()

    method_in_code = (
        f"requests.{method_lower}(" in code_no_comments
        or f"httpx.{method_lower}(" in code_no_comments
        or f".{method_lower}(" in code_no_comments
    )
    path_in_code = path_stem.lower() in code_no_comments if path_stem else True

    print(f"\n  Endpoint: {ep}")
    print(f"    method={method}, path={path}")
    print(f"    path_stem='{path_stem}'")
    print(f"    method_in_code={method_in_code} (looking for 'requests.{method_lower}(' or '.{method_lower}(')")
    print(f"    path_in_code={path_in_code} (looking for '{path_stem.lower()}' in code)")

    # Show what's actually in the code
    for pattern in [f"requests.{method_lower}", f".{method_lower}(", path_stem.lower()[:30]]:
        if pattern and pattern in code_no_comments:
            # find the line
            for line in code_no_comments.split("\n"):
                if pattern in line:
                    print(f"    FOUND '{pattern}' in line: {line.strip()[:100]}")
                    break

# Now check twilio_t2_lap-standard (uses requests, ep_in_code=0)
print("\n\n" + "=" * 100)
print("DEEP DIVE: twilio_t2_lap-standard - uses requests library, ep_in_code=0")
print("=" * 100)

data2 = index["twilio_t2_lap-standard"]
text2 = data2["execution"]["output_text"]
found_eps2 = data2["score"]["found_endpoints"]

print(f"Found endpoints: {found_eps2}")
code2 = extract_code_blocks(text2)
print(f"\nExtracted code ({len(code2)} chars):")
print(code2[:2000])

for ep in found_eps2:
    ep_norm = normalize_path(ep)
    parts = ep_norm.split(None, 1)
    if len(parts) != 2:
        continue
    method, path = parts
    path_stem = re.sub(r"\{[^}]+\}", "", path).rstrip("/")
    method_lower = method.lower()
    code_lines = [ln for ln in code2.split("\n") if not ln.lstrip().startswith("#")]
    code_no_comments = "\n".join(code_lines).lower()

    method_in_code = (
        f"requests.{method_lower}(" in code_no_comments
        or f"httpx.{method_lower}(" in code_no_comments
        or f".{method_lower}(" in code_no_comments
    )
    path_in_code = path_stem.lower() in code_no_comments if path_stem else True

    print(f"\n  Endpoint: {ep}")
    print(f"    path_stem='{path_stem}'")
    print(f"    method_in_code={method_in_code}")
    print(f"    path_in_code={path_in_code}")


# Check figma_t1_none
print("\n\n" + "=" * 100)
print("DEEP DIVE: figma_t1_none - uses requests, ep_in_code=0")
print("=" * 100)

data3 = index["figma_t1_none"]
text3 = data3["execution"]["output_text"]
found_eps3 = data3["score"]["found_endpoints"]

print(f"Found endpoints: {found_eps3}")
code3 = extract_code_blocks(text3)

for ep in found_eps3:
    ep_norm = normalize_path(ep)
    parts = ep_norm.split(None, 1)
    if len(parts) != 2:
        print(f"  {ep}: could not split")
        continue
    method, path = parts
    path_stem = re.sub(r"\{[^}]+\}", "", path).rstrip("/")
    method_lower = method.lower()
    code_lines = [ln for ln in code3.split("\n") if not ln.lstrip().startswith("#")]
    code_no_comments = "\n".join(code_lines).lower()

    method_in_code = (
        f"requests.{method_lower}(" in code_no_comments
        or f"httpx.{method_lower}(" in code_no_comments
        or f".{method_lower}(" in code_no_comments
    )
    path_in_code = path_stem.lower() in code_no_comments if path_stem else True

    print(f"\n  Endpoint: {ep}")
    print(f"    path_stem='{path_stem}'")
    print(f"    method_in_code={method_in_code}")
    print(f"    path_in_code={path_in_code}")

    if not path_in_code:
        # search for partial path
        path_parts = path_stem.split("/")
        for part in path_parts:
            if len(part) > 3 and part.lower() in code_no_comments:
                print(f"    Partial match: '{part}' found in code")
