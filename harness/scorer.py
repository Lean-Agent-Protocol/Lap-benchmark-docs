#!/usr/bin/env python3
"""
Automated scoring for benchmark runs.

Scoring components (0.0 - 1.0):
  - Endpoint identification (60%): Did agent find each target endpoint?
  - Parameter accuracy (30%): Fraction of expected params mentioned per endpoint
  - Code quality (10%): Has runnable code block, uses correct library, no hallucinated endpoints
"""

import re


def normalize_path(path: str) -> str:
    """Normalize an endpoint path for comparison.

    Strips leading/trailing whitespace, lowercases method,
    normalizes path parameter syntax ({id} vs :id vs <id>).
    """
    path = path.strip()
    # Normalize path params: :id -> {id}, <id> -> {id}
    path = re.sub(r":(\w+)", r"{\1}", path)
    path = re.sub(r"<(\w+)>", r"{\1}", path)
    # Remove trailing slashes
    path = path.rstrip("/")
    return path


def extract_endpoints_from_output(text: str) -> list[str]:
    """Extract Method + Endpoint pairs from agent output.

    Looks for patterns like:
      Method: POST
      Endpoint: /v1/charges
    or:
      CALL 1:
        Method: POST
        Endpoint: /v1/charges
    """
    endpoints = []

    # Pattern 1: Method: X / Endpoint: Y (on consecutive or near lines)
    method_pattern = re.compile(r"Method:\s*(\S+)", re.IGNORECASE)
    endpoint_pattern = re.compile(r"Endpoint:\s*(\S+)", re.IGNORECASE)

    methods = method_pattern.findall(text)
    paths = endpoint_pattern.findall(text)

    for m, p in zip(methods, paths):
        endpoints.append(normalize_path(f"{m.upper()} {p}"))

    # Pattern 2: HTTP method + path in code blocks (e.g., POST /v1/charges)
    code_pattern = re.compile(
        r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/\S+)",
        re.IGNORECASE,
    )
    for m, p in code_pattern.findall(text):
        ep = normalize_path(f"{m.upper()} {p}")
        if ep not in endpoints:
            endpoints.append(ep)

    # Pattern 3: RPC/GraphQL/AsyncAPI patterns
    rpc_pattern = re.compile(r"\b(RPC|QUERY|MUTATION|SUBSCRIBE|PUBLISH)\s+(\w+)", re.IGNORECASE)
    for m, name in rpc_pattern.findall(text):
        ep = f"{m.upper()} {name}"
        if ep not in endpoints:
            endpoints.append(ep)

    return endpoints


def score_endpoints(found: list[str], expected: list[str]) -> float:
    """Score endpoint identification. Binary per endpoint, averaged.

    Returns 0.0 - 1.0.
    """
    if not expected:
        return 1.0

    norm_found = [normalize_path(e) for e in found]
    hits = 0

    for exp in expected:
        exp_norm = normalize_path(exp)
        # Try exact match first
        if exp_norm in norm_found:
            hits += 1
            continue
        # Try partial match (path only, ignoring method for flexible matching)
        exp_parts = exp_norm.split(None, 1)
        if len(exp_parts) == 2:
            exp_method, exp_path = exp_parts
            for f in norm_found:
                f_parts = f.split(None, 1)
                if len(f_parts) == 2 and f_parts[0] == exp_method and f_parts[1] == exp_path:
                    hits += 1
                    break
                # Path-only match (method might differ in notation)
                if len(f_parts) == 2 and f_parts[1] == exp_path:
                    hits += 0.5
                    break

    return min(hits / len(expected), 1.0)


def extract_structured_sections(text: str) -> str:
    """Extract CALL blocks and code blocks -- the structured output sections.

    Excludes free prose (Plan, Notes) where common words like
    'from', 'to', 'name' appear naturally.
    """
    parts = []

    # Extract CALL blocks (untagged fenced blocks)
    call_blocks = re.findall(r"```\n(.*?)```", text, re.DOTALL)
    parts.extend(call_blocks)

    # Extract code blocks (language-tagged)
    code_blocks = re.findall(r"```\w+\n(.*?)```", text, re.DOTALL)
    parts.extend(code_blocks)

    return "\n".join(parts)


def score_params(text: str, expected_params: dict) -> float:
    """Score parameter accuracy using word-boundary matching in structured sections.

    Only searches CALL blocks and code blocks (not free prose) to avoid
    false positives from common words like 'from', 'to', 'name', 'id'.

    Args:
        text: Agent output text.
        expected_params: {"METHOD /path": ["param1", "param2"]}

    Returns 0.0 - 1.0.
    """
    if not expected_params:
        return 1.0

    structured = extract_structured_sections(text)
    structured_lower = structured.lower()

    total = 0
    found = 0

    for endpoint, params in expected_params.items():
        for param in params:
            total += 1
            p = param.lower()

            # Word-boundary match: param as a standalone word/identifier
            # Matches: "from", "from:", "\"from\"", "'from'", param=from
            # Rejects: "information", "platform", "transform"
            if re.search(rf'(?<![a-z_]){re.escape(p)}(?![a-z_])', structured_lower):
                found += 1

    return found / total if total > 0 else 1.0


def extract_code_blocks(text: str) -> str:
    """Extract Python code blocks from text (language-tagged blocks only).

    Skips untagged blocks (like CALL blocks) to avoid matching
    endpoint paths in prose that happen to be inside fences.
    """
    blocks = re.findall(r"```(?:python|py)\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return "\n".join(blocks)


def score_code_quality(
    text: str,
    target_endpoints: list[str] | None = None,
    expected_params: dict | None = None,
) -> dict:
    """Score code correctness by verifying endpoints and params IN code blocks.

    Returns dict with:
      - total: 0.0-1.0 overall code score
      - endpoints_in_code: fraction of target endpoints found in code
      - params_in_code: fraction of expected params found in code
      - has_code: bool
      - no_hallucination: bool
    """
    code = extract_code_blocks(text)
    code_lower = code.lower()

    has_code = len(code.strip()) > 0

    # 1. Endpoints in code (0.4) -- check method + path in code blocks
    #    Strip comments to avoid false matches on explanatory text
    code_lines = [ln for ln in code.split("\n") if not ln.lstrip().startswith("#")]
    code_no_comments = "\n".join(code_lines).lower()

    ep_hits = 0
    ep_total = len(target_endpoints) if target_endpoints else 0
    if target_endpoints and has_code:
        for ep in target_endpoints:
            ep_norm = normalize_path(ep)
            parts = ep_norm.split(None, 1)
            if len(parts) != 2:
                continue
            method, path = parts

            # Strip path params for matching: /emails/{email_id} -> /emails/
            path_stem = re.sub(r"\{[^}]+\}", "", path).rstrip("/")

            # Check method call: requests.post(, requests.get(, etc.
            method_lower = method.lower()
            method_in_code = (
                f"requests.{method_lower}(" in code_no_comments
                or f"httpx.{method_lower}(" in code_no_comments
                or f".{method_lower}(" in code_no_comments
            )

            # Check path appears in code (string literals, f-strings)
            path_in_code = path_stem.lower() in code_no_comments if path_stem else True

            if method_in_code and path_in_code:
                ep_hits += 1
            elif path_in_code:
                ep_hits += 0.5  # path found but method unclear

    ep_score = ep_hits / ep_total if ep_total > 0 else 1.0

    # 2. Params in code (0.4) -- check param names appear in code blocks
    param_hits = 0
    param_total = 0
    if expected_params and has_code:
        for endpoint, params in expected_params.items():
            for param in params:
                param_total += 1
                # Check param name in code (as dict key, kwarg, variable, etc.)
                # Match: "param", 'param', param=, param:
                param_lower = param.lower()
                if (
                    param_lower in code_lower
                    or param_lower.replace("_", "-") in code_lower
                ):
                    param_hits += 1

    param_score = param_hits / param_total if param_total > 0 else 1.0

    # 3. No hallucination (0.2) -- check full text, not just code
    hallucination_markers = [
        r"I don'?t have (access|information)",
        r"this endpoint (doesn'?t|does not) exist",
        r"I'?m (not sure|unable)",
        r"hallucinated",
    ]
    no_hallucination = not any(
        re.search(p, text, re.IGNORECASE) for p in hallucination_markers
    )

    # Weighted total
    total = 0.0
    if has_code:
        total += 0.4 * ep_score + 0.4 * param_score
    if no_hallucination:
        total += 0.2

    return {
        "total": round(total, 3),
        "endpoints_in_code": round(ep_score, 3),
        "params_in_code": round(param_score, 3),
        "has_code": has_code,
        "no_hallucination": no_hallucination,
    }


def score_run(
    agent_output: str,
    target_endpoints: list[str],
    expected_params: dict,
    weights: dict | None = None,
) -> dict:
    """Score a complete benchmark run.

    Args:
        agent_output: Full text output from the agent.
        target_endpoints: List of expected "METHOD /path" strings.
        expected_params: {"METHOD /path": ["param1", ...]}
        weights: Optional override for {endpoint, param, code} weights.

    Returns:
        {total, endpoint, params, code} scores (0.0 - 1.0 each)
    """
    if weights is None:
        weights = {"endpoint": 0.6, "param": 0.3, "code": 0.1}

    found_endpoints = extract_endpoints_from_output(agent_output)
    ep_score = score_endpoints(found_endpoints, target_endpoints)
    param_score = score_params(agent_output, expected_params)
    code_detail = score_code_quality(agent_output, target_endpoints, expected_params)
    code_score = code_detail["total"]

    total = (
        weights["endpoint"] * ep_score
        + weights["param"] * param_score
        + weights["code"] * code_score
    )

    return {
        "total": round(total, 3),
        "endpoint": round(ep_score, 3),
        "params": round(param_score, 3),
        "code": round(code_score, 3),
        "code_detail": code_detail,
        "found_endpoints": found_endpoints,
    }
