#!/usr/bin/env python3
"""Comprehensive cross-tier comparison and SDK pattern analysis."""

import json
import os
import glob
import re

run_dir = os.path.join(os.path.dirname(__file__), "runs", "20260213_003225")
files = glob.glob(os.path.join(run_dir, "*.json"))

# Build data
results = []
for f in sorted(files):
    fname = os.path.basename(f)
    if fname == "manifest.json":
        continue
    with open(f, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    spec_id = data.get("spec_id")
    tier = data.get("tier")
    task_id = data.get("task_id")
    score = data.get("score", {})
    code_detail = score.get("code_detail", {})
    text = data.get("execution", {}).get("output_text", "")

    # Detect what library the code uses
    code_blocks = re.findall(r"```(?:python|py)\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    code_text = "\n".join(code_blocks).lower()

    uses_requests = "requests." in code_text
    uses_sdk = False
    sdk_name = ""
    if "twilio" in code_text and ("client." in code_text or "from twilio" in code_text):
        uses_sdk = True
        sdk_name = "twilio-sdk"
    elif "stripe." in code_text and ("stripe.customer" in code_text or "stripe.charge" in code_text or "stripe.api_key" in code_text):
        uses_sdk = True
        sdk_name = "stripe-sdk"
    elif "figma" in code_text and "requests." in code_text:
        uses_sdk = False
        sdk_name = "requests+figma"

    results.append({
        "spec_id": spec_id,
        "tier": tier,
        "task_id": task_id,
        "code_total": code_detail.get("total", 0),
        "ep_in_code": code_detail.get("endpoints_in_code", 0),
        "params_in_code": code_detail.get("params_in_code", 0),
        "has_code": code_detail.get("has_code", False),
        "no_hallucination": code_detail.get("no_hallucination", True),
        "uses_requests": uses_requests,
        "uses_sdk": uses_sdk,
        "sdk_name": sdk_name,
        "total_score": score.get("total", 0),
        "endpoint_score": score.get("endpoint", 0),
    })

tier_order = ["none", "pretty", "minified", "lap-standard", "lap-lean"]

# ANALYSIS: SDK vs requests library usage correlation with ep_in_code
print("=" * 100)
print("ANALYSIS: Library choice vs endpoints_in_code score (only runs with has_code=True)")
print("=" * 100)
print()
print(f"{'spec_id':20s} {'task':5s} {'tier':14s} | {'library':18s} | {'ep_in_code':10s} | {'params':7s} | {'code_total':10s}")
print("-" * 100)

code_runs = [r for r in results if r["has_code"]]
for r in sorted(code_runs, key=lambda x: (x["spec_id"], x["task_id"], tier_order.index(x["tier"]) if x["tier"] in tier_order else 99)):
    lib = r["sdk_name"] if r["uses_sdk"] else ("requests" if r["uses_requests"] else "unknown")
    print(f"{r['spec_id']:20s} {r['task_id']:5s} {r['tier']:14s} | {lib:18s} | {r['ep_in_code']:10.3f} | {r['params_in_code']:7.3f} | {r['code_total']:10.3f}")

# Summary: SDK vs requests
print()
print("=" * 100)
print("SUMMARY: SDK usage vs requests library - impact on endpoints_in_code")
print("=" * 100)

sdk_runs = [r for r in code_runs if r["uses_sdk"]]
requests_runs = [r for r in code_runs if r["uses_requests"] and not r["uses_sdk"]]

if sdk_runs:
    avg_ep_sdk = sum(r["ep_in_code"] for r in sdk_runs) / len(sdk_runs)
    avg_params_sdk = sum(r["params_in_code"] for r in sdk_runs) / len(sdk_runs)
    avg_total_sdk = sum(r["code_total"] for r in sdk_runs) / len(sdk_runs)
    zero_ep_sdk = sum(1 for r in sdk_runs if r["ep_in_code"] == 0)
    print(f"SDK code (n={len(sdk_runs)}): avg_ep_in_code={avg_ep_sdk:.3f}, zero_ep={zero_ep_sdk}/{len(sdk_runs)}, avg_params={avg_params_sdk:.3f}, avg_code_total={avg_total_sdk:.3f}")
    for r in sdk_runs:
        print(f"  {r['spec_id']:15s} {r['task_id']:5s} {r['tier']:14s} sdk={r['sdk_name']:15s} ep={r['ep_in_code']:.3f}")

if requests_runs:
    avg_ep_req = sum(r["ep_in_code"] for r in requests_runs) / len(requests_runs)
    avg_params_req = sum(r["params_in_code"] for r in requests_runs) / len(requests_runs)
    avg_total_req = sum(r["code_total"] for r in requests_runs) / len(requests_runs)
    zero_ep_req = sum(1 for r in requests_runs if r["ep_in_code"] == 0)
    print(f"\nrequests library (n={len(requests_runs)}): avg_ep_in_code={avg_ep_req:.3f}, zero_ep={zero_ep_req}/{len(requests_runs)}, avg_params={avg_params_req:.3f}, avg_code_total={avg_total_req:.3f}")

# Cross-tier comparison for the same spec+task
print()
print("=" * 100)
print("CROSS-TIER COMPARISON: Same spec+task across all tiers")
print("=" * 100)

from collections import defaultdict
by_spec_task = defaultdict(dict)
for r in results:
    by_spec_task[f"{r['spec_id']}_{r['task_id']}"][r["tier"]] = r

for key in sorted(by_spec_task.keys()):
    tiers = by_spec_task[key]
    has_any_code = any(t.get("has_code", False) for t in tiers.values())
    if not has_any_code:
        continue  # skip specs with no code at all

    print(f"\n--- {key} ---")
    for tier in tier_order:
        if tier in tiers:
            r = tiers[tier]
            lib = r["sdk_name"] if r["uses_sdk"] else ("requests" if r["uses_requests"] else "none")
            code_mark = "CODE" if r["has_code"] else "----"
            print(f"  {tier:14s}: [{code_mark}] ep={r['ep_in_code']:.3f} params={r['params_in_code']:.3f} code_total={r['code_total']:.3f} lib={lib:15s} | overall={r['total_score']:.3f} (ep_score={r['endpoint_score']:.3f})")

# LAP-specific analysis
print()
print("=" * 100)
print("LAP vs NON-LAP CODE QUALITY (only runs with has_code=True)")
print("=" * 100)
lap_tiers = {"lap-standard", "lap-lean"}
nonlap_tiers = {"none", "pretty", "minified"}

lap_code = [r for r in code_runs if r["tier"] in lap_tiers]
nonlap_code = [r for r in code_runs if r["tier"] in nonlap_tiers]

for label, group in [("NON-LAP", nonlap_code), ("LAP", lap_code)]:
    if not group:
        continue
    n = len(group)
    avg_ep = sum(r["ep_in_code"] for r in group) / n
    avg_params = sum(r["params_in_code"] for r in group) / n
    avg_total = sum(r["code_total"] for r in group) / n
    zero_ep = sum(1 for r in group if r["ep_in_code"] == 0)
    sdk_n = sum(1 for r in group if r["uses_sdk"])
    req_n = sum(1 for r in group if r["uses_requests"] and not r["uses_sdk"])
    print(f"{label:8s} (n={n:2d}): ep_in_code={avg_ep:.3f}, params={avg_params:.3f}, code_total={avg_total:.3f}, zero_ep={zero_ep}/{n}, sdk_usage={sdk_n}/{n}, requests_usage={req_n}/{n}")
