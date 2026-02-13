#!/usr/bin/env python3
"""
Claude Code CLI executor for benchmark runs.

Each run:
  1. Creates an isolated temp directory (UUID-based, unpredictable)
  2. Agent fetches doc via GitHub raw URL (no local file copy)
  3. Builds prompt from template
  4. Executes claude -p with the prompt
  5. Captures stdout, stderr, wall time
  6. Locates and copies the JSONL session recording
  7. Cleans up temp directory
"""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def generate_run_id(spec_id: str, tier: str, task_id: str) -> str:
    """Deterministic run ID for reproducibility."""
    key = f"{spec_id}:{tier}:{task_id}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def build_prompt(
    doc_ref: str,
    task_description: str,
    template_path: Path | None = None,
    *,
    local: bool = False,
) -> str:
    """Build the agent prompt from template.

    Args:
        doc_ref: URL to fetch (default) or local file path (if local=True).
        task_description: The task text.
        template_path: Path to prompt template. Uses default if None.
        local: If True, doc_ref is a local path; instruct agent to Read.

    Returns:
        Complete prompt string.
    """
    if template_path is None:
        template_path = PROJECT_ROOT / "prompts" / "template.md"

    template = template_path.read_text(encoding="utf-8")
    if doc_ref is None:
        # No-doc baseline: agent must work from prior knowledge only
        instruction = "No documentation is provided. Use your best knowledge of this API to complete the task."
    elif local:
        filename = Path(doc_ref).name
        instruction = f"The API documentation is available as a local file in your workspace: {filename}\nRead it using the Read tool."
    else:
        instruction = f"Fetch the API documentation from this URL: {doc_ref}"
    return template.replace("{DOC_INSTRUCTION}", instruction).replace("{TASK}", task_description)


def find_session_jsonl(work_dir: str, session_id: str | None = None) -> Path | None:
    """Find the JSONL session recording for a run.

    Claude Code stores sessions at:
      ~/.claude/projects/<project-hash>/<session-id>.jsonl

    If session_id is known (from JSON output), search for that exact file.
    Otherwise fall back to most recently modified .jsonl.
    """
    claude_dir = Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        return None

    # If we have a session_id, search for the exact file
    if session_id:
        for proj_dir in claude_dir.iterdir():
            if not proj_dir.is_dir():
                continue
            candidate = proj_dir / f"{session_id}.jsonl"
            if candidate.exists():
                return candidate

    # Fallback: most recently modified .jsonl
    candidates = []
    for proj_dir in claude_dir.iterdir():
        if not proj_dir.is_dir():
            continue
        for jsonl in proj_dir.glob("*.jsonl"):
            candidates.append(jsonl)

    if not candidates:
        return None

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def execute_run(
    spec_id: str,
    tier: str,
    task_id: str,
    task_description: str,
    doc_path: Path | None,
    doc_url: str | None = None,
    model: str = "claude-sonnet-4-5-20250929",
    timeout: int = 180,
    allowed_tools: list[str] | None = None,
    local: bool = False,
) -> dict:
    """Execute a single benchmark run.

    Args:
        spec_id: Spec identifier (e.g., "stripe")
        tier: Compression tier (pretty, minified, lap-standard, lap-lean)
        task_id: Task identifier (e.g., "t1")
        task_description: The task text
        doc_path: Path to the compiled doc variant (used for local mode or fallback)
        doc_url: GitHub raw URL for the compiled doc (preferred for isolation)
        model: Claude model ID
        timeout: Max seconds for the run
        allowed_tools: Tools to allow the agent
        local: If True, copy doc locally instead of using URL delivery

    Returns:
        Run result dict with execution metrics and output.
    """
    run_id = generate_run_id(spec_id, tier, task_id)

    if allowed_tools is None:
        allowed_tools = ["Bash", "Read", "Write", "Glob", "Grep", "WebFetch"]

    # Create isolated temp directory with double-UUID nesting.
    # Structure: %TEMP%/<uuid-outer>/<uuid-inner>/workspace/
    # Agent runs in workspace/. Going up:
    #   ../       = <uuid-inner>  (empty besides workspace/)
    #   ../../    = <uuid-outer>  (empty besides <uuid-inner>/)
    #   ../../../ = %TEMP% root   (3 levels deep -- harder to discover siblings)
    # Even if discovered, sibling dirs contain only prompt.txt (docs come via URL).
    outer = Path(tempfile.gettempdir()) / str(uuid.uuid4())
    parent = outer / str(uuid.uuid4())
    parent.mkdir(parents=True)
    work_dir = parent / "workspace"
    work_dir.mkdir()

    result = {
        "run_id": run_id,
        "spec_id": spec_id,
        "tier": tier,
        "task_id": task_id,
        "model": model,
        "work_dir": str(work_dir),
        "doc_path": str(doc_path) if doc_path else None,
        "doc_url": doc_url,
        "execution": {
            "status": "pending",
            "wall_time_s": 0,
            "stdout": "",
            "stderr": "",
        },
    }

    try:
        # Build prompt based on tier
        if tier == "none":
            # No-doc baseline: no documentation provided
            prompt = build_prompt(None, task_description)
        elif local or not doc_url:
            # Local file delivery with neutral filename
            doc_dest = work_dir / "api_docs.txt"
            shutil.copy2(doc_path, doc_dest)
            prompt = build_prompt(str(doc_dest), task_description, local=True)
        else:
            prompt = build_prompt(doc_url, task_description, local=False)

        prompt_path = work_dir / "prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")

        # Build claude command
        tools_str = ",".join(allowed_tools)
        cmd = [
            "claude",
            "-p", f"@{prompt_path}",
            "--model", model,
            "--allowedTools", tools_str,
            "--output-format", "json",
        ]

        # Execute
        start_time = time.time()
        proc = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env={**os.environ, "CLAUDE_CODE_DISABLE_NONESSENTIAL": "1"},
        )
        wall_time = time.time() - start_time

        result["execution"]["wall_time_s"] = round(wall_time, 2)
        result["execution"]["stdout"] = proc.stdout
        result["execution"]["stderr"] = proc.stderr
        result["execution"]["return_code"] = proc.returncode
        result["execution"]["status"] = "completed" if proc.returncode == 0 else "error"

        # Parse JSON output from claude --output-format json
        try:
            output_data = json.loads(proc.stdout)
            if isinstance(output_data, dict):
                result["execution"]["output_text"] = output_data.get("result", proc.stdout)
                result["execution"]["session_id"] = output_data.get("session_id")
                result["execution"]["num_turns"] = output_data.get("num_turns", 0)
                result["execution"]["cost_usd"] = output_data.get("total_cost_usd", 0)
                result["execution"]["cli_duration_ms"] = output_data.get("duration_ms", 0)
                usage = output_data.get("usage", {})
                result["execution"]["input_tokens"] = usage.get("input_tokens", 0)
                result["execution"]["output_tokens"] = usage.get("output_tokens", 0)
                result["execution"]["cache_creation_tokens"] = usage.get("cache_creation_input_tokens", 0)
                result["execution"]["cache_read_tokens"] = usage.get("cache_read_input_tokens", 0)
                result["execution"]["total_tokens"] = (
                    usage.get("input_tokens", 0)
                    + usage.get("output_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0)
                )
            else:
                result["execution"]["output_text"] = proc.stdout
        except json.JSONDecodeError:
            result["execution"]["output_text"] = proc.stdout

    except subprocess.TimeoutExpired:
        result["execution"]["status"] = "timeout"
        result["execution"]["wall_time_s"] = timeout
    except Exception as e:
        result["execution"]["status"] = "error"
        result["execution"]["error"] = str(e)
    finally:
        # Try to capture JSONL recording using session_id from output
        try:
            session_id = result.get("execution", {}).get("session_id")
            jsonl_path = find_session_jsonl(str(work_dir), session_id=session_id)
            if jsonl_path and jsonl_path.exists():
                result["recording"] = {
                    "source_jsonl": str(jsonl_path),
                    "jsonl_size_bytes": jsonl_path.stat().st_size,
                }
        except Exception:
            pass

        # Cleanup: remove the outer UUID dir and all contents
        try:
            shutil.rmtree(outer, ignore_errors=True)
        except Exception:
            pass

    return result


def save_run_result(result: dict, output_dir: Path):
    """Save a run result to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = result["run_id"]
    path = output_dir / f"{run_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    return path


def copy_recording(result: dict, recordings_dir: Path) -> Path | None:
    """Copy JSONL recording to the results directory."""
    recording = result.get("recording", {})
    source = recording.get("source_jsonl")
    if not source or not Path(source).exists():
        return None

    recordings_dir.mkdir(parents=True, exist_ok=True)
    run_id = result["run_id"]
    dest = recordings_dir / f"{run_id}.jsonl"
    shutil.copy2(source, dest)
    return dest
