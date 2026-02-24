# LAP Benchmark v2 - Implementation Plan

## Context

The current benchmark (26 specs, 5 formats, 62 tasks, OpenClaw-based) needs a major overhaul to become a robust, reproducible research benchmark. The new system will test whether LAP-compressed API documentation enables AI agents to complete real-world integration tasks as effectively as verbose originals -- while consuming significantly fewer tokens.

**What prompted this:** LAP has matured to v0.3 with 5 format compilers and two compression modes (Standard + Lean). We need rigorous evidence across many real APIs, multiple compression tiers, and multiple models.

**Intended outcome:** A benchmark suite with 100+ real production API specs, automated execution via Claude Code CLI, automated scoring, and publication-ready analysis comparing 4 compression tiers across 5 formats.

---

## Benchmark Matrix

| Dimension | Values | Count |
|-----------|--------|-------|
| **Formats** | OpenAPI, AsyncAPI, GraphQL, Postman, Protobuf/gRPC | 5 |
| **Specs per format** | 20+ real production APIs | 100+ |
| **Compression tiers** | Pretty, Minified, LAP Standard, LAP Lean | 4 |
| **Tasks per spec** | 2 tasks, each with 2 endpoints from different doc sections | 2 |
| **Models (phased)** | Sonnet 4.5 (first), then Opus 4.6, then Codex 5.3 | 3 |
| **Total runs (Sonnet)** | 100 specs x 4 tiers x 2 tasks | ~800 |

**JSON Schema:** Excluded from v2.0 (no LAP compiler exists). Can add in v2.1 if a `jsonschema.py` compiler is built. Documented as known limitation.

---

## Project Structure

```
c:\LAP\Lap-benchmark-docs\
├── registry/                      # Spec registry
│   ├── registry.yaml             # Central metadata (all specs)
│   └── manifests/                # Per-spec task definitions
│       ├── openapi/
│       │   ├── stripe.yaml
│       │   ├── twilio.yaml
│       │   └── ...
│       ├── asyncapi/
│       ├── graphql/
│       ├── postman/
│       └── protobuf/
│
├── sources/                       # Raw source specs from GitHub
│   ├── openapi/
│   ├── asyncapi/
│   ├── graphql/
│   ├── postman/
│   └── protobuf/
│
├── compiled/                      # Generated doc variants (4 tiers)
│   ├── openapi/
│   │   └── stripe/
│   │       ├── pretty.yaml
│   │       ├── minified.yaml
│   │       ├── standard.lap
│   │       └── lean.lap
│   └── ... (same per format/spec)
│
├── harness/                       # Benchmark execution system
│   ├── __init__.py
│   ├── runner.py                 # Batch orchestrator + checkpointing
│   ├── executor.py               # Claude Code CLI wrapper + isolation
│   ├── scorer.py                 # Automated output scoring
│   ├── metrics.py                # Token counting, static metrics
│   ├── jsonl_parser.py           # Parse JSONL recordings for precise metrics
│   ├── minifier.py               # Format-aware whitespace stripping
│   └── config.yaml               # Runtime configuration
│
├── prompts/
│   └── template.md               # Agent prompt template
│
├── results/
│   ├── runs/                     # Per-batch run results
│   │   └── {batch_id}/
│   │       ├── manifest.json
│   │       └── {run_id}.json
│   └── analysis/                 # Aggregated reports
│
├── scripts/
│   ├── fetch_sources.py          # Download specs from GitHub URLs
│   ├── compile_variants.py       # Generate all 4 compression tiers
│   ├── validate_registry.py      # Validate registry + manifests
│   └── analyze.py                # Generate analysis reports
│
├── verbose/                       # Legacy (keep for now)
├── doclean/                       # Legacy (keep for now)
└── README.md
```

---

## Key Components

### 1. Spec Registry (`registry/registry.yaml`)

Central metadata for every spec:

```yaml
specs:
  stripe:
    format: openapi
    github_url: https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.yaml
    size_class: large        # small <50KB, medium 50-500KB, large >500KB
    endpoint_count: 198
    domain: payments
```

### 2. Task Manifests (`registry/manifests/{format}/{spec}.yaml`)

Per-spec task definitions with ground truth for scoring:

```yaml
spec_id: stripe
tasks:
  - id: t1
    description: "I need to charge a customer $49.99 on their saved card and then look up the charge status to confirm it went through."
    target_endpoints:
      - POST /v1/charges
      - GET /v1/charges/{id}
    expected_params:
      POST /v1/charges: [amount, currency, customer]
      GET /v1/charges/{id}: [id]
  - id: t2
    description: "List all charges for a specific customer from this month and process a partial refund on the most recent one."
    target_endpoints:
      - GET /v1/charges
      - POST /v1/refunds
    expected_params:
      GET /v1/charges: [customer, created, limit]
      POST /v1/refunds: [charge, amount]
```

**Task rules:**
- Exactly 2 tasks per spec
- Each task uses exactly 2 endpoints from different sections of the doc
- Tasks are realistic integration scenarios a developer would face
- Endpoints chosen to test scanning (spread apart in doc)

### 3. Compression Tiers

| Tier | What it is | How to generate |
|------|-----------|----------------|
| **Pretty** | Original spec, properly formatted | Copy from `sources/` |
| **Minified** | Whitespace-stripped, comments removed | `harness/minifier.py` (format-aware) |
| **LAP Standard** | Full LAP with descriptions | `lap compile spec -o standard.lap` |
| **LAP Lean** | Types-only LAP, no descriptions | `lap compile spec --lean -o lean.lap` |

**Minifier details** per format:
- YAML (OpenAPI/AsyncAPI): strip comments, collapse multi-line strings, remove blank lines
- JSON (Postman): `json.dumps(data, separators=(',',':'))`
- GraphQL: strip comments, collapse whitespace
- Protobuf: strip comments, collapse whitespace

### 4. Agent Executor

Each run:
1. Create isolated temp dir: `%TEMP%\lap_bench_{run_id}\`
2. Build prompt from template + GitHub raw URL for the compiled doc variant
3. Execute: `claude -p @prompt.txt --allowedTools bash,Read,Write,Glob,Grep,WebFetch`
4. Capture: stdout, stderr, wall time
5. Parse Claude Code output for token usage and tool call count
6. Locate and copy the JSONL session file to `results/runs/{batch_id}/recordings/{run_id}.jsonl`
7. Parse JSONL for precise metrics: per-turn tokens, tool call count, total turns

**Isolation:** Temp dir is NOT under `Lap-benchmark-docs/`. Agent has no access to other specs, tasks, or results.

### 5. JSONL Black Box Recording

Every run's full conversation history is preserved as a JSONL file for reproducibility and post-hoc investigation.

**How Claude Code stores history:**
- Per-session files at: `~/.claude/projects/<project-path>/<session-id>.jsonl`
- Contains every message (user/assistant), tool calls, tool results, token usage, timestamps
- Subagent conversations stored separately in `<session-id>/subagents/`

**Capture strategy:**
1. Executor generates a deterministic `session-id` per run (e.g., `bench-{run_id}`)
2. Pass `--session-id {session_id}` to Claude Code CLI (if supported), otherwise parse session ID from output
3. After run completes, copy the JSONL file from `~/.claude/projects/` to results:
   ```
   results/runs/{batch_id}/recordings/{run_id}.jsonl
   ```
4. Also copy any subagent JSONL files to `recordings/{run_id}/subagents/`

**What this enables:**
- Replay exact agent behavior for any run
- Extract precise token counts per turn (input_tokens, output_tokens from `usage` field)
- Count tool calls by parsing `tool_use` messages
- Investigate failures: see exactly where agent went wrong
- Compare agent strategies across compression tiers
- Audit for hallucinations: trace which doc sections agent read before producing output

**Updated results structure:**
```
results/runs/{batch_id}/
├── manifest.json
├── {run_id}.json            # Scored result summary
└── recordings/
    ├── {run_id}.jsonl       # Full conversation history (black box)
    └── {run_id}/
        └── subagents/       # If agent spawned subagents
            └── agent-{id}.jsonl
```

### 6. Scoring (0.0 - 1.0)

| Component | Weight | How |
|-----------|--------|-----|
| **Endpoint ID** | 60% | Binary: did agent find each of the 2 target endpoints? |
| **Param accuracy** | 30% | Fraction of expected params mentioned per endpoint |
| **Code quality** | 10% | Has runnable code block, uses correct library, no hallucinated endpoints |

**Extraction:** Parse agent output for `Method:` and `Endpoint:` patterns (from the mandated output format), match against ground truth with path normalization.

### 7. Metrics Per Run

```json
{
  "run_id": "abc123",
  "spec_id": "stripe",
  "format": "openapi",
  "tier": "lap-standard",
  "task_id": "t1",
  "model": "claude-sonnet-4-5-20250929",
  "static": {
    "doc_bytes": 4521,
    "doc_tokens": 1203,
    "compression_ratio": 3.2
  },
  "execution": {
    "wall_time_s": 18.3,
    "input_tokens": 1450,
    "output_tokens": 320,
    "total_tokens": 1770,
    "tool_calls": 3,
    "status": "completed"
  },
  "score": {
    "total": 0.85,
    "endpoint": 1.0,
    "params": 0.75,
    "code": 0.8
  },
  "recording": {
    "jsonl_path": "recordings/abc123.jsonl",
    "jsonl_size_bytes": 45230,
    "subagent_recordings": [],
    "turn_count": 7
  }
}
```

---

## Implementation Phases

### Phase 0: Save plan to project

1. Copy this plan to `c:\LAP\Lap-benchmark-docs\BENCHMARK_PLAN.md` for version control

### Phase 1: Foundation (registry + compilation pipeline)

1. Create directory structure
2. Implement `registry/registry.yaml` schema with existing 26 specs
3. Create manifests for existing specs (port from `benchmark_tasks.yaml`)
4. Implement `scripts/validate_registry.py`
5. Implement `harness/minifier.py` (format-aware whitespace stripping)
6. Implement `scripts/compile_variants.py` (calls LAP CLI for standard+lean, minifier for minified)
7. Generate all 4 tiers for existing 26 specs = 104 doc variants
8. Implement `harness/metrics.py` (static token counting with tiktoken)

### Phase 2: Harness core (executor + runner)

1. Implement `harness/executor.py` (Claude Code CLI wrapper + JSONL capture)
2. Implement `harness/jsonl_parser.py` (parse JSONL for per-turn tokens, tool calls, turn count)
3. Implement `harness/runner.py` (batch orchestrator with prioritization + checkpointing)
4. Implement `prompts/template.md` (agent prompt with mandatory output format)
5. Implement `harness/config.yaml`
6. End-to-end test: 1 spec, 1 tier, 1 task = single run
7. Verify JSONL capture works (file is copied, parseable, metrics extracted)
8. Fix issues found in e2e test

### Phase 3: Scoring

1. Implement `harness/scorer.py` (endpoint extraction, param matching, code quality heuristics)
2. Integrate scorer into runner pipeline
3. Run pilot: 6 specs x 4 tiers x 2 tasks = 48 runs (Sonnet)
4. Manually verify 20 scored results, tune scoring logic

### Phase 4: Spec collection (expand to 100+)

1. Research and curate 20+ real specs per format
2. Download sources via `scripts/fetch_sources.py`
3. Create manifests with 2 realistic tasks each
4. Compile all 4 tiers
5. Validate compilation (no errors, reasonable compression)

### Phase 5: Full Sonnet run

1. Execute all ~800 runs with Sonnet (batched, big specs first)
2. Concurrency: 3 parallel agents, rate-limited
3. Checkpoint every 10 runs (resume on failure)
4. Monitor, fix failures, retry

### Phase 6: Analysis + reporting

1. Implement `scripts/analyze.py`
2. Generate publication-ready charts
3. Key research questions answered

### Phase 7: Multi-model expansion

1. Re-run full matrix with Opus 4.6
2. Model comparison analysis
3. Prepare for OpenAI Codex 5.3 integration (future)

---

## Execution Configuration

```yaml
# harness/config.yaml
model: claude-sonnet-4-5-20250929
concurrency: 3
timeout_seconds: 180
retry_attempts: 2
priority_order: size_desc  # large specs first
tiers: [pretty, minified, lap-standard, lap-lean]
formats: [openapi, asyncapi, graphql, postman, protobuf]
claude_cli:
  allowed_tools: [bash, Read, Write, Glob, Grep, WebFetch]
scoring:
  endpoint_weight: 0.6
  param_weight: 0.3
  code_weight: 0.1
  success_threshold: 0.7
```

---

## Verification Plan

1. **Registry validation:** `python scripts/validate_registry.py` -- checks all specs have sources, manifests, 2 tasks each
2. **Compilation validation:** `python scripts/compile_variants.py --validate` -- checks all 4 tiers generate without errors
3. **Single run test:** Execute 1 spec/1 tier/1 task manually, inspect output and scoring
4. **Pilot batch:** 6 specs (2 small, 2 medium, 2 large) x 4 tiers x 2 tasks = 48 runs
5. **Scoring accuracy:** Manually review 20 pilot results, confirm scoring matches human judgment
6. **Full run:** Monitor first 50 runs of full batch, verify stability before unattended execution

---

## Critical Dependencies

- **LAP core** (`c:\lap\lap`): Used for compilation. CLI: `lap compile`, Python API: `from core.compilers import compile`
- **Claude Code CLI**: Must be available as `claude` command. Uses Max subscription (rate limits apply)
- **tiktoken**: For token counting (static metrics)
- **Python 3.10+**: All scripts

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Rate limiting on Max subscription | Conservative concurrency (3), exponential backoff |
| Scoring inaccuracy | Manual spot-check 20+ runs, iterative tuning |
| AsyncAPI: hard to find 20 real specs | Accept fewer if needed, document in limitations |
| Agent ignores output format | Robust regex parsing, fallback to full-text search for endpoints |
| Minification breaks spec parsing | Validate minified output loads correctly before using |
