# LAP Benchmark Docs

API documentation in two formats for benchmarking [LAP (Lean Agent Protocol)](https://github.com/lean-agent-protocol/lap).

## Structure

- `verbose/` — Raw OpenAPI YAML specs (original format)
- `doclean/` — DocLean compiled versions (LAP format)

## Specs

| API | Endpoints | Verbose Size | DocLean Size | Compression |
|-----|-----------|-------------|-------------|-------------|
| stripe-charges | 5 | 11KB | 4KB | 2.6x |
| github-core | 6 | 12KB | 4KB | 3.2x |
| discord | 4 | 5KB | 1KB | 3.4x |
| petstore | 19 | 22KB | 6KB | 3.9x |
| twitter | 80 | 287KB | 63KB | 4.6x |
| resend | 70 | 108KB | 21KB | 5.1x |
| launchdarkly | 105 | 137KB | 54KB | 2.6x |
| snyk | 103 | 1,015KB | 39KB | 26.3x |
| hetzner | 144 | 1,128KB | 79KB | 14.3x |
| plaid | 198 | 1,491KB | 212KB | 7.1x |

## Usage

Raw URLs for fetching:
```
https://raw.githubusercontent.com/lean-agent-protocol/benchmark-docs/main/verbose/{spec}.yaml
https://raw.githubusercontent.com/lean-agent-protocol/benchmark-docs/main/doclean/{spec}.doclean
```
