# LAP Benchmark

> **[View Full Benchmark Report](https://lap-platform.github.io/Lap-benchmark-docs/results/LAP_Benchmark_v2_Full_Report.html)** -- 500 runs, 50 specs, 5 formats

Measures how well [LAP-compressed](https://github.com/Lap-Platform/lap) API documentation performs compared to original formats when given to AI coding agents.

## Benchmark Matrix

- **50** production API specs across **5** formats (OpenAPI, AsyncAPI, GraphQL, Postman, Protobuf)
- **5** documentation tiers (4 compression levels + no-doc baseline)
- **2** tasks per spec = **500 runs** per model
- Automated scoring: endpoint identification 60%, parameter accuracy 30%, code quality 10%

## Documentation Tiers

| Tier | Description |
|------|-------------|
| None | No documentation provided (prior-knowledge baseline) |
| Pretty | Original spec, properly formatted |
| Minified | Whitespace and comments stripped |
| LAP Standard | Full LAP format with descriptions |
| LAP Lean | LAP format, types only (maximum compression) |

## Spec Coverage

### OpenAPI (10)

Figma, Stripe, Twilio, GitHub REST, DigitalOcean, Slack, Spotify, Box, Plaid, Resend

### AsyncAPI (10)

Streetlights, Slack RTM, Adeo Kafka, Social Media, Gitter Streaming, Gemini WebSocket, Kraken WebSocket, Correlation ID, Operation Security, RPC Server

### GraphQL (10)

GitHub, SWAPI, Yelp, Shopify, Artsy, Linear, Saleor, Elasticsearch, Coral, Unraid

### Postman (10)

Twilio, Postman Echo, Adobe, SAP, Stripe, Azure DevOps, Auth0, Braintree, InfluxDB, Akeneo

### Protobuf / gRPC (10)

Google Storage, Pub/Sub, Vision, Data Catalog, Translate, Spanner, Firestore, Talent, Language, Billing

## Project Structure

```
registry/       Spec definitions + task manifests with ground truth
sources/        Raw specs fetched from GitHub
compiled/       200 doc variants (50 specs x 4 tiers)
harness/        Benchmark runner, executor, scorer
prompts/        Agent prompt template
scripts/        Compilation, validation, analysis
results/        Benchmark results and reports
```

## Quick Start

```bash
pip install tiktoken pyyaml   # dependencies

# Compile all doc variants
python scripts/compile_variants.py

# Validate registry + manifests
python scripts/validate_registry.py

# Pilot run (7 specs, all tiers)
python -m harness.runner --pilot

# Full run (50 specs, all tiers)
python -m harness.runner --full
```

## Scoring

Each run produces a score from 0.0 to 1.0 across three components:

- **Endpoint identification (60%)** - Did the agent call the correct API endpoint?
- **Parameter accuracy (30%)** - Did the agent use the right parameters? Matched via word-boundary detection in structured CALL blocks and code blocks only.
- **Code quality (10%)** - Does the generated Python code reference the correct endpoints and parameters?

## Confounding Variable Controls

- **No-doc baseline** - `none` tier measures what the model knows without any documentation
- **Neutral filenames** - All docs delivered as `api_docs.txt` (no tier or format leakage)
- **Business-language tasks** - Task descriptions avoid endpoint-revealing technical terms
- **Python only** - Eliminates language choice as a variable
- **No library hints** - Prompt says "appropriate libraries", not specific package names
- **Word-boundary param matching** - Parameters scored only in structured sections, not free prose

## Status

Pilot completed: 70 runs across 7 specs, all 5 tiers. Full benchmark run pending.
