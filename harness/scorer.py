#!/usr/bin/env python3
"""
Automated scoring for benchmark runs.

Scoring components (0.0 - 1.0):
  - Endpoint identification (35%): Did agent find each target endpoint?
  - Parameter accuracy (30%): Fraction of expected params mentioned per endpoint
  - Code quality (35%): Are the correct endpoints+params present in code blocks?

Endpoint identification checks BOTH structured output (CALL blocks) AND code blocks.
Code quality scoring is protocol-agnostic: checks path/channel segments in code,
not library-specific patterns like requests.get() or KafkaConsumer().
"""

import re

# Normalize AsyncAPI method abbreviations to full form
_ASYNC_METHOD_ALIASES = {
    "SUB": "SUBSCRIBE",
    "PUB": "PUBLISH",
}


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
        # Normalize SUB->SUBSCRIBE, PUB->PUBLISH
        m_upper = m.upper()
        # Strip trailing parens/punctuation from method (e.g., "PUBLISH" from "PUBLISH)")
        m_clean = re.sub(r"[^A-Z]", "", m_upper)
        m_norm = _ASYNC_METHOD_ALIASES.get(m_clean, m_clean)
        endpoints.append(normalize_path(f"{m_norm} {p}"))

    # Pattern 2: HTTP method + path in code blocks (e.g., POST /v1/charges)
    code_pattern = re.compile(
        r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/\S+)",
        re.IGNORECASE,
    )
    for m, p in code_pattern.findall(text):
        ep = normalize_path(f"{m.upper()} {p}")
        if ep not in endpoints:
            endpoints.append(ep)

    # Pattern 3: RPC/GraphQL patterns (single-word operation names)
    rpc_pattern = re.compile(r"\b(RPC|QUERY|MUTATION)\s+(\w+)", re.IGNORECASE)
    for m, name in rpc_pattern.findall(text):
        ep = f"{m.upper()} {name}"
        if ep not in endpoints:
            endpoints.append(ep)

    # Pattern 4: AsyncAPI SUBSCRIBE/PUBLISH/SUB/PUB with channel paths
    async_pattern = re.compile(
        r"\b(SUBSCRIBE|PUBLISH|SUB|PUB)\s+[/]?\s*([\w./{}\-]+)",
        re.IGNORECASE,
    )
    for m, channel in async_pattern.findall(text):
        method = _ASYNC_METHOD_ALIASES.get(m.upper(), m.upper())
        ep = f"{method} {channel}"
        if ep not in endpoints:
            endpoints.append(ep)

    # Pattern 5: Channel/Topic lines (agents often put channels on separate lines)
    channel_pattern = re.compile(r"(?:Channel|Topic):\s*([\w./{}\-:]+)", re.IGNORECASE)
    for channel in channel_pattern.findall(text):
        if len(channel) > 5:  # skip trivial matches
            ep = f"CHANNEL {channel}"
            if ep not in endpoints:
                endpoints.append(ep)

    # Pattern 6: Operation lines (e.g., "Operation: receiveLightMeasurement")
    op_pattern = re.compile(r"Operation:\s*(\w+)", re.IGNORECASE)
    for op in op_pattern.findall(text):
        ep = f"OPERATION {op}"
        if ep not in endpoints:
            endpoints.append(ep)

    return endpoints


def _extract_channel_key(endpoint: str) -> str | None:
    """Extract the meaningful operation/channel name from an AsyncAPI endpoint.

    Examples:
        'SUBSCRIBE smartylighting.streetlights.1.0.event.{id}.lighting.measured'
            -> 'lighting.measured'
        'PUBLISH / outgoingMessage' -> 'outgoingmessage'
        'SUBSCRIBE / message' -> 'message'
    """
    parts = endpoint.split(None, 1)
    if len(parts) != 2:
        return None
    method, path = parts
    if method.upper() not in ("SUBSCRIBE", "PUBLISH", "SUB", "PUB"):
        return None
    path = path.strip().strip("/").strip()
    # For long dotted paths, take last 2 segments as the key
    segments = [s for s in path.split(".") if s and not s.startswith("{")]
    if len(segments) >= 2:
        return ".".join(segments[-2:]).lower()
    return segments[-1].lower() if segments else None


def _extract_path_key_segments(path: str) -> list[str]:
    """Extract meaningful segments from a path (REST or dotted AsyncAPI).

    Protocol-agnostic: works for /v1/activity_logs, dotted.channel.names,
    gRPC service methods, etc.

    Returns lowercased segments, filtered to skip short/version/numeric noise.
    """
    # Determine separator
    if "/" in path:
        raw_segments = path.split("/")
    else:
        raw_segments = path.split(".")

    segments = []
    for seg in raw_segments:
        if not seg or seg.startswith("{"):
            continue
        seg_clean = re.sub(r"\.\w+$", "", seg).lower()
        # Skip: short (<=2), version prefixes (v1, v2), pure numbers (1, 0)
        if len(seg_clean) <= 2:
            continue
        if re.match(r"^v\d", seg_clean) or re.match(r"^\d+$", seg_clean):
            continue
        segments.append(seg_clean)

    return segments


def score_endpoints(found: list[str], expected: list[str], full_text: str = "") -> float:
    """Score endpoint identification. Binary per endpoint, averaged.

    Checks BOTH structured output (CALL blocks) AND code blocks for endpoints.
    Code-based matches get full credit since working code proves understanding.

    Args:
        found: Extracted endpoint strings from agent output.
        expected: Expected endpoint strings from manifest.
        full_text: Full agent output text (for code block and fallback checks).

    Returns 0.0 - 1.0.
    """
    if not expected:
        return 1.0

    norm_found = [normalize_path(e) for e in found]
    found_text = " ".join(norm_found).lower()
    structured = extract_structured_sections(full_text).lower() if full_text else ""
    code = extract_code_blocks(full_text).lower() if full_text else ""
    # Strip comments from code for reliable matching
    code_no_comments = "\n".join(
        ln for ln in code.split("\n") if not ln.lstrip().startswith("#")
    )
    hits = 0

    for exp in expected:
        exp_norm = normalize_path(exp)
        # Try exact match first
        if exp_norm in norm_found:
            hits += 1
            continue

        exp_parts = exp_norm.split(None, 1)
        if len(exp_parts) != 2:
            continue

        exp_method, exp_path = exp_parts
        matched = False

        # Try method+path match (including SUB/PUB normalization)
        for f in norm_found:
            f_parts = f.split(None, 1)
            if len(f_parts) != 2:
                continue
            f_method = _ASYNC_METHOD_ALIASES.get(f_parts[0], f_parts[0])
            exp_method_norm = _ASYNC_METHOD_ALIASES.get(exp_method, exp_method)

            if f_method == exp_method_norm and f_parts[1] == exp_path:
                hits += 1
                matched = True
                break
            # Path-only match from CALL blocks
            if f_parts[1] == exp_path:
                hits += 0.5
                matched = True
                break

        if matched:
            continue

        # Code-based check: do the path's key segments appear in code?
        # This is protocol-agnostic -- works for REST, Kafka, gRPC, etc.
        path_segments = _extract_path_key_segments(exp_path)
        if path_segments and code_no_comments:
            if all(seg in code_no_comments for seg in path_segments):
                hits += 1
                continue

        # AsyncAPI channel fuzzy matching: match on channel key segments
        channel_key = _extract_channel_key(exp)
        if channel_key:
            search_corpus = found_text + " " + structured + " " + code_no_comments
            if channel_key in search_corpus:
                hits += 1
                continue
            for seg in channel_key.split("."):
                if len(seg) > 4 and seg in search_corpus:
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


def _extract_resource_name(path: str) -> str | None:
    """Extract the primary resource name from an API path.

    Examples:
        /v1/customers -> customers
        /v1/customers/{customer}/balance_transactions -> balance_transactions
        /2010-04-01/Accounts/{AccountSid}/Messages.json -> messages
        /v1/emails/{email_id} -> emails
    """
    # Strip path params and version prefixes
    segments = [s for s in path.split("/") if s and not s.startswith("{")]
    if not segments:
        return None
    # Take the last meaningful segment (the resource)
    resource = segments[-1]
    # Strip file extensions (.json, .xml)
    resource = re.sub(r"\.\w+$", "", resource)
    return resource.lower()


def _check_path_segments_in_code(path: str, code: str) -> bool:
    """Check if meaningful path segments appear in code.

    Protocol-agnostic: handles both slash-separated REST paths and
    dot-separated AsyncAPI/gRPC paths.

    Handles REST: /2010-04-01/Accounts/{AccountSid}/Messages.json
      -> checks: 'accounts', 'messages' (skipping version prefix and params)

    Handles AsyncAPI: smartylighting.streetlights.1.0.action.{id}.turn.off
      -> checks: 'smartylighting', 'streetlights', 'action', 'turn'
    """
    segments = _extract_path_key_segments(path)

    if not segments:
        return True  # No meaningful segments to check

    # All meaningful segments must appear in code
    return all(seg in code for seg in segments)


def score_code_quality(
    text: str,
    target_endpoints: list[str] | None = None,
    expected_params: dict | None = None,
) -> dict:
    """Score code correctness by verifying endpoints and params IN code blocks.

    Protocol-agnostic: checks path/channel segments in code rather than
    looking for specific library patterns. Works for REST, Kafka, gRPC,
    MQTT, GraphQL, or any future protocol.

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

    # 1. Endpoints in code (0.4) -- check path/channel segments in code blocks
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

            # Protocol-agnostic: check if path segments appear in code
            path_in_code = _check_path_segments_in_code(path, code_no_comments)

            # Also check method presence (protocol-agnostic patterns)
            method_lower = method.lower()
            method_in_code = (
                # REST: requests.get(, httpx.post(, etc.
                f"requests.{method_lower}(" in code_no_comments
                or f"httpx.{method_lower}(" in code_no_comments
                or f".{method_lower}(" in code_no_comments
                # AsyncAPI: any mention of subscribe/publish/consumer/producer
                or (method_lower in ("subscribe", "sub") and (
                    "consumer" in code_no_comments
                    or "subscribe" in code_no_comments
                ))
                or (method_lower in ("publish", "pub") and (
                    "producer" in code_no_comments
                    or "publish" in code_no_comments
                    or ".send(" in code_no_comments
                ))
                # GraphQL
                or (method_lower in ("query", "mutation") and
                    method_lower in code_no_comments)
                # RPC
                or (method_lower == "rpc" and "grpc" in code_no_comments)
            )

            # SDK detection: check for SDK-style calls referencing the resource
            resource = _extract_resource_name(path)
            sdk_in_code = False
            if resource:
                sdk_actions = [".create(", ".list(", ".retrieve(", ".fetch(", ".get(",
                              ".update(", ".delete(", ".send("]
                for action in sdk_actions:
                    if re.search(
                        rf'\.{re.escape(resource)}{re.escape(action)}',
                        code_no_comments,
                    ):
                        sdk_in_code = True
                        break
                    singular = resource.rstrip("s")
                    if singular != resource and re.search(
                        rf'\.{re.escape(singular)}{re.escape(action)}',
                        code_no_comments,
                    ):
                        sdk_in_code = True
                        break

            if path_in_code and (method_in_code or sdk_in_code):
                ep_hits += 1
            elif path_in_code:
                ep_hits += 0.75  # path found, method direction unclear
            elif sdk_in_code:
                ep_hits += 0.75  # SDK call found but path segments unclear

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
        weights = {"endpoint": 0.35, "param": 0.3, "code": 0.35}

    found_endpoints = extract_endpoints_from_output(agent_output)
    ep_score = score_endpoints(found_endpoints, target_endpoints, full_text=agent_output)
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
