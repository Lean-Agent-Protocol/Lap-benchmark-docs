#!/usr/bin/env python3
"""
Spawn all benchmark agents for the full run.
Outputs a shell script of sessions_spawn commands, or JSON manifest.
"""
import yaml, json, os

BENCH_DIR = '/data/workspace/lap-benchmark-docs'
VERBOSE_DIR = os.path.join(BENCH_DIR, 'verbose')
DOCLEAN_DIR = os.path.join(BENCH_DIR, 'doclean')

EXT_MAP = {
    'openapi': '.yaml', 'asyncapi': '.yaml',
    'graphql': '.graphql', 'postman': '.json', 'protobuf': '.proto',
}

PROMPT_TEMPLATE = """You are an API integration assistant. A user has given you API documentation and a task.

Your job: solve the task using ONLY the provided documentation. Do not make up endpoints, fields, or parameters that aren't in the docs.

## Output Format (MANDATORY)

Your response MUST follow this exact structure:

### Plan
Brief description of what API calls are needed and in what order.

### API Calls
For each API call, provide:

```
CALL {{n}}:
  Method: {{method}}
  Endpoint: {{path}}
  Parameters: {{required params with example values}}
  Body: {{request body if applicable}}
  Expected Response: {{key fields from response}}
```

### Code Example
Complete, runnable code example that implements the full task.

### Notes
Any important caveats, rate limits, auth requirements, or edge cases from the docs.

---
IMPORTANT: Only use endpoints/operations that exist in the provided documentation. If the task requires something not in the docs, say so explicitly.

## Documentation

Read the file at {doc_path}

## Task

{task}

Solve this task now. Follow the output format exactly. When done, output BENCHMARK_COMPLETE as the last line."""

with open(os.path.join(BENCH_DIR, 'benchmark_tasks.yaml')) as f:
    all_tasks = yaml.safe_load(f)

runs = []
for spec_name, spec in sorted(all_tasks.items()):
    ctype = spec['type']
    ext = EXT_MAP[ctype]
    for task_idx, task in enumerate(spec['tasks']):
        for variant in ['verbose', 'doclean']:
            if variant == 'verbose':
                doc_path = os.path.join(VERBOSE_DIR, f'{spec_name}{ext}')
            else:
                doc_path = os.path.join(DOCLEAN_DIR, f'{spec_name}.doclean')
            
            prompt = PROMPT_TEMPLATE.format(doc_path=doc_path, task=task)
            label = f"full-{spec_name}-t{task_idx}-{variant}"
            
            runs.append({
                'label': label,
                'spec': spec_name,
                'type': ctype,
                'variant': variant,
                'task_idx': task_idx,
                'task': task,
                'doc_path': doc_path,
                'prompt': prompt,
                'prompt_len': len(prompt),
            })

# Save manifest
manifest_path = os.path.join(BENCH_DIR, 'results', 'full_run_manifest.json')
os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
with open(manifest_path, 'w') as f:
    json.dump({'total': len(runs), 'runs': runs}, f, indent=2)

print(f"Total runs: {len(runs)}")
print(f"Manifest: {manifest_path}")

# Stats
by_type = {}
for r in runs:
    by_type.setdefault(r['type'], 0)
    by_type[r['type']] += 1
for t, c in sorted(by_type.items()):
    print(f"  {t}: {c} runs")
