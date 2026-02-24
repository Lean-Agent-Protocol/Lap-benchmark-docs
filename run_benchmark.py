#!/usr/bin/env python3
"""
DocLean Benchmark Runner v3
Spawns agents with verbose vs doclean docs, tracks tokens/time.
Results are reproducible JSON files.

Usage:
  python3 run_benchmark.py --pilot          # 3 specs, 1 task each = 6 runs
  python3 run_benchmark.py --full           # all specs, all tasks
  python3 run_benchmark.py --spec snyk      # single spec
"""
import sys, os, json, yaml, time, argparse, hashlib
from datetime import datetime, timezone

BENCH_DIR = '/data/workspace/lap-benchmark-docs'
RESULTS_DIR = os.path.join(BENCH_DIR, 'results')
VERBOSE_DIR = os.path.join(BENCH_DIR, 'verbose')
DOCLEAN_DIR = os.path.join(BENCH_DIR, 'doclean')

# File extension map
EXT_MAP = {
    'openapi': '.yaml',
    'asyncapi': '.yaml',
    'graphql': '.graphql',
    'postman': '.json',
    'protobuf': '.proto',
}

SYSTEM_PROMPT = """You are an API integration assistant. You will be given API documentation and a task.

Your job: solve the task using ONLY the provided documentation. Do not make up endpoints, fields, or parameters that aren't in the docs.

## Output Format (MANDATORY)

Your response MUST follow this exact structure:

### Plan
Brief description of what API calls are needed and in what order.

### API Calls
For each API call, provide:

```
CALL {n}:
  Method: {HTTP_METHOD/RPC_TYPE/PUB|SUB/QUERY|MUTATION}
  Endpoint: {path or channel or operation name}
  Parameters: {required params with example values}
  Body: {request body if applicable}
  Expected Response: {key fields from response}
```

### Code Example
Complete, runnable code example (Python preferred, or appropriate language for the protocol) that implements the full task.

### Notes
Any important caveats, rate limits, auth requirements, or edge cases from the docs.

---
IMPORTANT: Only use endpoints/operations that exist in the provided documentation. If the task requires something not in the docs, say so explicitly.
"""

def load_tasks():
    with open(os.path.join(BENCH_DIR, 'benchmark_tasks.yaml')) as f:
        return yaml.safe_load(f)

def get_doc_content(spec_name, doc_type, variant):
    """Load verbose or doclean doc content."""
    if variant == 'verbose':
        ext = EXT_MAP.get(doc_type, '.yaml')
        path = os.path.join(VERBOSE_DIR, f'{spec_name}{ext}')
    else:
        path = os.path.join(DOCLEAN_DIR, f'{spec_name}.doclean')
    
    with open(path, 'r') as f:
        return f.read(), os.path.getsize(path)

def build_prompt(doc_content, task, doc_type, variant):
    """Build the full prompt with embedded docs."""
    doc_label = "Raw API Documentation" if variant == 'verbose' else "DocLean Compressed Documentation"
    return f"""{SYSTEM_PROMPT}

## {doc_label} ({doc_type})

<documentation>
{doc_content}
</documentation>

## Task

{task}

Solve this task now. Follow the output format exactly."""

def generate_run_id(spec_name, variant, task_idx):
    """Deterministic run ID for reproducibility."""
    key = f"{spec_name}:{variant}:{task_idx}"
    return hashlib.md5(key.encode()).hexdigest()[:8]

def create_run_manifest(specs_to_run, all_tasks):
    """Create a manifest of all runs to execute."""
    runs = []
    for spec_name in specs_to_run:
        spec = all_tasks[spec_name]
        for task_idx, task in enumerate(spec['tasks']):
            for variant in ['verbose', 'doclean']:
                run_id = generate_run_id(spec_name, variant, task_idx)
                runs.append({
                    'run_id': run_id,
                    'spec': spec_name,
                    'type': spec['type'],
                    'variant': variant,
                    'task_idx': task_idx,
                    'task': task,
                })
    return runs

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--pilot', action='store_true', help='3 specs × 1 task × 2 variants = 6 runs')
    group.add_argument('--full', action='store_true', help='All specs, all tasks')
    group.add_argument('--spec', type=str, help='Single spec name')
    parser.add_argument('--dry-run', action='store_true', help='Print manifest without running')
    args = parser.parse_args()
    
    all_tasks = load_tasks()
    
    if args.pilot:
        # Pick 3 specs: 1 small OpenAPI, 1 large OpenAPI, 1 non-OpenAPI
        pilot_specs = ['petstore', 'snyk', 'proto-google-storage']
        # Only first task per spec for pilot
        for s in pilot_specs:
            all_tasks[s]['tasks'] = all_tasks[s]['tasks'][:1]
        specs_to_run = pilot_specs
    elif args.spec:
        if args.spec not in all_tasks:
            print(f"Unknown spec: {args.spec}")
            print(f"Available: {', '.join(sorted(all_tasks.keys()))}")
            sys.exit(1)
        specs_to_run = [args.spec]
    else:
        specs_to_run = sorted(all_tasks.keys())
    
    runs = create_run_manifest(specs_to_run, all_tasks)
    
    # Create results dir
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    batch_dir = os.path.join(RESULTS_DIR, f'batch_{timestamp}')
    os.makedirs(batch_dir, exist_ok=True)
    
    # Save manifest
    manifest = {
        'batch_id': timestamp,
        'created': datetime.now(timezone.utc).isoformat(),
        'total_runs': len(runs),
        'specs': specs_to_run,
        'runs': runs,
    }
    manifest_path = os.path.join(batch_dir, 'manifest.json')
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Batch: {timestamp}")
    print(f"Specs: {len(specs_to_run)}")
    print(f"Total runs: {len(runs)}")
    print(f"Manifest: {manifest_path}")
    print()
    
    if args.dry_run:
        print("=== DRY RUN — Manifest ===")
        for r in runs:
            doc_content, doc_size = get_doc_content(r['spec'], r['type'], r['variant'])
            prompt = build_prompt(doc_content, r['task'], r['type'], r['variant'])
            print(f"  [{r['run_id']}] {r['spec']}:{r['variant']} task#{r['task_idx']} | doc={doc_size:,}B prompt={len(prompt):,}chars")
        return
    
    # Generate prompt files for each run (so agents can be spawned externally)
    for r in runs:
        doc_content, doc_size = get_doc_content(r['spec'], r['type'], r['variant'])
        prompt = build_prompt(doc_content, r['task'], r['type'], r['variant'])
        
        run_file = os.path.join(batch_dir, f"{r['run_id']}_{r['spec']}_{r['variant']}.json")
        run_data = {
            **r,
            'prompt': prompt,
            'prompt_chars': len(prompt),
            'doc_size_bytes': doc_size,
            'status': 'pending',
        }
        with open(run_file, 'w') as f:
            json.dump(run_data, f, indent=2)
    
    print(f"Generated {len(runs)} run files in {batch_dir}")
    print(f"\nTo spawn agents, use: python3 spawn_agents.py {batch_dir}")

if __name__ == '__main__':
    main()
