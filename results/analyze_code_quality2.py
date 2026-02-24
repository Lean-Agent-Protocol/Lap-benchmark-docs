#!/usr/bin/env python3
"""Find specific files by spec+tier+task and show code analysis."""

import json
import os
import glob
import re

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

# CASE 1: Twilio t1 lap-lean (has_code=True, ep_in_code=0)
print("=" * 100)
print("CASE 1: twilio_t1_lap-lean - endpoints_in_code=0, has_code=True")
print("=" * 100)
data = index["twilio_t1_lap-lean"]
text = data["execution"]["output_text"]

# Show target endpoints from the score
score = data["score"]
print(f"Found endpoints (by scorer): {score.get('found_endpoints', [])}")
print(f"Code detail: {score.get('code_detail', {})}")
print()

# Extract python code blocks
code_blocks = re.findall(r"```(?:python|py)\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
print(f"Number of python code blocks: {len(code_blocks)}")
for i, block in enumerate(code_blocks):
    print(f"\n--- Python Block {i+1} (first 1500 chars) ---")
    print(block[:1500])

# Now let's check: what does the scorer actually check?
# It needs: requests.post( or httpx.post( or .post(
# and the path stem
print("\n\nSCORER ANALYSIS for twilio t1:")
# The expected endpoints from the structured output are
# POST /2010-04-01/Accounts/{AccountSid}/Messages.json
# GET /2010-04-01/Accounts/{AccountSid}/Messages/{Sid}.json

# Strip comments
code_lines = [ln for ln in (code_blocks[0] if code_blocks else "").split("\n") if not ln.lstrip().startswith("#")]
code_no_comments = "\n".join(code_lines).lower()
print(f"Contains 'requests.post(': {'requests.post(' in code_no_comments}")
print(f"Contains '.post(': {'.post(' in code_no_comments}")
print(f"Contains '.get(': {'.get(' in code_no_comments}")
print(f"Contains '/2010-04-01/accounts': {'/2010-04-01/accounts' in code_no_comments}")
print(f"Contains '/messages': {'/messages' in code_no_comments}")
print(f"Contains 'client.messages.create': {'client.messages.create' in code_no_comments}")

# The issue: Twilio SDK uses client.messages.create(), NOT requests.post("/2010-04-01/...")
# The scorer only looks for requests.post( or httpx.post( or .post(
# client.messages.create( matches NONE of these patterns!

print("\n\n" + "=" * 100)
print("CASE 2: stripe_t1_lap-lean - endpoints_in_code=1.0 (SUCCESS)")
print("=" * 100)
data2 = index["stripe_t1_lap-lean"]
text2 = data2["execution"]["output_text"]
score2 = data2["score"]
print(f"Found endpoints (by scorer): {score2.get('found_endpoints', [])}")
print(f"Code detail: {score2.get('code_detail', {})}")
print()
code_blocks2 = re.findall(r"```(?:python|py)\n(.*?)```", text2, re.DOTALL | re.IGNORECASE)
for i, block in enumerate(code_blocks2):
    print(f"--- Python Block {i+1} (first 1500 chars) ---")
    print(block[:1500])

code_lines2 = [ln for ln in (code_blocks2[0] if code_blocks2 else "").split("\n") if not ln.lstrip().startswith("#")]
code_no_comments2 = "\n".join(code_lines2).lower()
print(f"\nContains 'requests.post(': {'requests.post(' in code_no_comments2}")
print(f"Contains '.post(': {'.post(' in code_no_comments2}")

print("\n\n" + "=" * 100)
print("CASE 3: stripe_t1_pretty - endpoints_in_code=0.0 (FAIL)")
print("=" * 100)
data3 = index["stripe_t1_pretty"]
text3 = data3["execution"]["output_text"]
score3 = data3["score"]
print(f"Found endpoints (by scorer): {score3.get('found_endpoints', [])}")
print(f"Code detail: {score3.get('code_detail', {})}")
print()
code_blocks3 = re.findall(r"```(?:python|py)\n(.*?)```", text3, re.DOTALL | re.IGNORECASE)
for i, block in enumerate(code_blocks3):
    print(f"--- Python Block {i+1} (first 1500 chars) ---")
    print(block[:1500])
if code_blocks3:
    code_lines3 = [ln for ln in code_blocks3[0].split("\n") if not ln.lstrip().startswith("#")]
    code_no_comments3 = "\n".join(code_lines3).lower()
    print(f"\nContains 'requests.post(': {'requests.post(' in code_no_comments3}")
    print(f"Contains '.post(': {'.post(' in code_no_comments3}")
    print(f"Contains 'stripe.': {'stripe.' in code_no_comments3}")

print("\n\n" + "=" * 100)
print("CASE 4: figma_t1_none - endpoints_in_code=0.0 (FAIL with has_code=True)")
print("=" * 100)
data4 = index["figma_t1_none"]
text4 = data4["execution"]["output_text"]
score4 = data4["score"]
print(f"Found endpoints (by scorer): {score4.get('found_endpoints', [])}")
print(f"Code detail: {score4.get('code_detail', {})}")
print()
code_blocks4 = re.findall(r"```(?:python|py)\n(.*?)```", text4, re.DOTALL | re.IGNORECASE)
for i, block in enumerate(code_blocks4):
    print(f"--- Python Block {i+1} (first 1500 chars) ---")
    print(block[:1500])
if code_blocks4:
    code_lines4 = [ln for ln in code_blocks4[0].split("\n") if not ln.lstrip().startswith("#")]
    code_no_comments4 = "\n".join(code_lines4).lower()
    print(f"\nContains 'requests.get(': {'requests.get(' in code_no_comments4}")
    print(f"Contains '.get(': {'.get(' in code_no_comments4}")
