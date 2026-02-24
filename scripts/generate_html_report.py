#!/usr/bin/env python3
"""Generate BENCHMARK_SPECS.html from registry + manifests."""

import yaml
from pathlib import Path

root = Path(__file__).resolve().parent.parent

with open(root / "registry/registry.yaml", encoding="utf-8") as f:
    reg = yaml.safe_load(f)

# Collect all data
specs_data = []
for spec_id, meta in reg["specs"].items():
    fmt = meta["format"]
    domain = meta.get("domain", "")
    sc = meta.get("size_class", "")
    gh_url = meta.get("github_url", "")

    sp = root / meta["source_file"]
    src_kb = round(sp.stat().st_size / 1024, 1) if sp.exists() else 0

    cdir = root / "compiled" / fmt / spec_id
    sizes = {"pretty": 0, "minified": 0, "standard": 0, "lean": 0}
    files = {"pretty": "", "minified": "", "standard": "", "lean": ""}
    if cdir.exists():
        for f in sorted(cdir.iterdir()):
            kb = round(f.stat().st_size / 1024, 1)
            n = f.name
            rel = f.relative_to(root).as_posix()
            if n.startswith("lean"):
                sizes["lean"] = kb
                files["lean"] = rel
            elif n.startswith("standard"):
                sizes["standard"] = kb
                files["standard"] = rel
            elif n.startswith("minified"):
                sizes["minified"] = kb
                files["minified"] = rel
            elif n.startswith("pretty"):
                sizes["pretty"] = kb
                files["pretty"] = rel

    # Read manifest
    mpath = root / "registry" / "manifests" / fmt / f"{spec_id}.yaml"
    tasks = []
    if mpath.exists():
        with open(mpath, encoding="utf-8") as mf:
            manifest = yaml.safe_load(mf)
        for t in manifest.get("tasks", []):
            tasks.append(t)

    specs_data.append(
        {
            "id": spec_id,
            "format": fmt,
            "domain": domain,
            "size_class": sc,
            "github_url": gh_url,
            "src_kb": src_kb,
            "sizes": sizes,
            "files": files,
            "tasks": tasks,
            "source_file": meta["source_file"],
        }
    )

formats = ["openapi", "asyncapi", "graphql", "postman", "protobuf"]
format_labels = {
    "openapi": "OpenAPI",
    "asyncapi": "AsyncAPI",
    "graphql": "GraphQL",
    "postman": "Postman",
    "protobuf": "Protobuf",
}

# Review notes
reviews = {
    "elastic-gql": (
        "NOTE",
        "Schema has only 3 root queries, each with single host param. Trivially simple but valid.",
    ),
    "postman-echo": (
        "NOTE",
        "Demo/echo API with minimal params. Serves as easy baseline.",
    ),
    "braintree-postman": (
        "NOTE",
        "All endpoints are POST /graphql (GraphQL-over-REST). Scorer distinguishes by operation name in brackets.",
    ),
    "gitter-streaming": (
        "NOTE",
        "Spec has 1 channel with 2 message types. t1/t2 share endpoints but test different payload fields.",
    ),
    "operation-security": (
        "NOTE",
        "Spec has 1 channel. t1 tests message structure, t2 tests nested payload schemas.",
    ),
    "rpc-server": (
        "NOTE",
        "t1/t2 swap PUBLISH/SUBSCRIBE roles (server vs client perspective). Same endpoints.",
    ),
    "correlation-id": (
        "NOTE",
        "Subset of streetlights with correlation ID focus. t1 tests payload, t2 tests channel params.",
    ),
    "websocket-gemini": (
        "NOTE",
        "Spec has 1 channel. t1 tests update payload fields, t2 tests WebSocket binding query params.",
    ),
    "adeo-kafka": (
        "NOTE",
        "Request-reply pattern. t1 focuses on request headers, t2 focuses on response timing metadata.",
    ),
}

# Escape HTML
def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# Build HTML
parts = []
parts.append(
    """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LAP Benchmark v2 - Spec Registry</title>
<style>
  :root { --bg: #0d1117; --fg: #c9d1d9; --accent: #58a6ff; --border: #30363d; --card: #161b22; --green: #3fb950; --yellow: #d29922; --red: #f85149; --muted: #8b949e; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; background: var(--bg); color: var(--fg); padding: 24px; line-height: 1.5; }
  h1 { color: #fff; margin-bottom: 8px; font-size: 28px; }
  h2 { color: var(--accent); margin: 32px 0 16px; font-size: 22px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
  h3 { color: #fff; margin: 24px 0 12px; font-size: 18px; }
  .subtitle { color: var(--muted); margin-bottom: 24px; }
  .totals { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 32px; }
  .stat { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; text-align: center; }
  .stat .num { font-size: 28px; font-weight: 700; color: var(--accent); }
  .stat .label { font-size: 13px; color: var(--muted); margin-top: 4px; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 14px; }
  th { background: var(--card); color: var(--accent); text-align: left; padding: 10px 12px; border: 1px solid var(--border); font-weight: 600; position: sticky; top: 0; z-index: 1; }
  td { padding: 8px 12px; border: 1px solid var(--border); vertical-align: top; }
  tr:hover td { background: rgba(88,166,255,0.05); }
  .kb { text-align: right; font-variant-numeric: tabular-nums; }
  .ratio { text-align: right; font-weight: 600; color: var(--green); }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500; }
  .tag-small { background: rgba(63,185,80,0.15); color: var(--green); }
  .tag-medium { background: rgba(210,153,34,0.15); color: var(--yellow); }
  .tag-large { background: rgba(248,81,73,0.15); color: var(--red); }
  .task { background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 12px 16px; margin: 8px 0; }
  .task-id { font-weight: 700; color: var(--accent); margin-right: 8px; }
  .task-desc { color: var(--fg); }
  .endpoints { margin-top: 8px; }
  .ep { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 13px; color: var(--green); background: rgba(63,185,80,0.08); padding: 2px 6px; border-radius: 3px; display: inline-block; margin: 2px 4px 2px 0; }
  .params { color: var(--muted); font-size: 13px; margin-top: 4px; }
  .param { font-family: monospace; color: var(--yellow); }
  .verdict { font-weight: 600; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
  .verdict-ok { background: rgba(63,185,80,0.15); color: var(--green); }
  .verdict-warn { background: rgba(210,153,34,0.15); color: var(--yellow); }
  .verdict-problem { background: rgba(248,81,73,0.15); color: var(--red); }
  .verdict-note { background: rgba(88,166,255,0.15); color: var(--accent); }
  .files { font-size: 12px; white-space: nowrap; }
  .files a { color: var(--muted); }
  .files a:hover { color: var(--accent); }
  .format-section { margin-bottom: 48px; }
  .na { color: var(--muted); font-style: italic; }
  details { margin: 8px 0; }
  summary { cursor: pointer; color: var(--accent); font-weight: 500; padding: 4px 0; }
  summary:hover { text-decoration: underline; }
  .review-note { background: rgba(88,166,255,0.08); border-left: 3px solid var(--accent); padding: 8px 12px; margin: 8px 0; font-size: 13px; color: var(--accent); border-radius: 0 4px 4px 0; }
  .review-warn { background: rgba(210,153,34,0.1); border-left: 3px solid var(--yellow); padding: 8px 12px; margin: 8px 0; font-size: 13px; color: var(--yellow); border-radius: 0 4px 4px 0; }
  .review-problem { background: rgba(248,81,73,0.1); border-left: 3px solid var(--red); padding: 8px 12px; margin: 8px 0; font-size: 13px; color: var(--red); border-radius: 0 4px 4px 0; }
</style>
</head>
<body>
<h1>LAP Benchmark v2 - Spec Registry</h1>
<p class="subtitle">50 real-world API specs across 5 formats, compiled into 194 variants for benchmarking</p>
"""
)

# Grand totals
parts.append('<div class="totals">')
for num, label in [
    ("50", "Total Specs"),
    ("5", "Formats"),
    ("100", "Tasks"),
    ("194", "Compiled Variants"),
    ("388", "Full Runs"),
    ("48", "Pilot Runs"),
]:
    parts.append(
        f'<div class="stat"><div class="num">{num}</div><div class="label">{label}</div></div>'
    )
parts.append("</div>")

# Format totals table
parts.append("<h2>Size Totals by Format</h2>")
parts.append(
    "<table><tr><th>Format</th><th>Count</th>"
    '<th class="kb">Source KB</th>'
    '<th class="kb">Minified KB</th><th class="kb">Std LAP KB</th>'
    '<th class="kb">Lean LAP KB</th><th class="kb">Lean Ratio</th></tr>'
)
grand = [0.0] * 4
for fmt in formats:
    fspecs = [s for s in specs_data if s["format"] == fmt]
    totals = [
        sum(s["src_kb"] for s in fspecs),
        sum(s["sizes"]["minified"] for s in fspecs),
        sum(s["sizes"]["standard"] for s in fspecs),
        sum(s["sizes"]["lean"] for s in fspecs),
    ]
    for i in range(4):
        grand[i] += totals[i]
    ratio = f"{totals[0]/totals[3]:.1f}x" if totals[3] > 0 else "N/A"
    parts.append(f"<tr><td>{format_labels[fmt]}</td><td>10</td>")
    for t in totals:
        parts.append(f'<td class="kb">{t:,.1f}</td>')
    parts.append(f'<td class="ratio">{ratio}</td></tr>')

ratio = f"{grand[0]/grand[3]:.1f}x" if grand[3] > 0 else "N/A"
parts.append(
    '<tr style="font-weight:700;background:var(--card)"><td>TOTAL</td><td>50</td>'
)
for g in grand:
    parts.append(f'<td class="kb">{g:,.1f}</td>')
parts.append(f'<td class="ratio">{ratio}</td></tr></table>')

# Per-format sections
for fmt in formats:
    fspecs = [s for s in specs_data if s["format"] == fmt]
    parts.append('<div class="format-section">')
    parts.append(f"<h2>{format_labels[fmt]} ({len(fspecs)} specs)</h2>")

    # Size table
    parts.append(
        "<table><tr><th>#</th><th>Spec</th><th>Domain</th><th>Size</th>"
        '<th class="kb">Source</th><th class="kb">Mini</th>'
        '<th class="kb">Std LAP</th><th class="kb">Lean LAP</th>'
        '<th class="kb">Ratio</th><th>Files</th></tr>'
    )
    for i, s in enumerate(fspecs, 1):
        tag_cls = f'tag-{s["size_class"]}' if s["size_class"] in ("small", "medium", "large") else ""
        lean = s["sizes"]["lean"]
        std = s["sizes"]["standard"]
        if lean > 0 and s["src_kb"] > 0:
            ratio = f"{s['src_kb']/lean:.1f}x"
        elif std > 0 and s["src_kb"] > 0:
            ratio = f"{s['src_kb']/std:.1f}x (std)"
        else:
            ratio = '<span class="na">N/A</span>'

        file_links = []
        if s["github_url"]:
            file_links.append(f'<a href="{esc(s["github_url"])}" target="_blank">source</a>')
        for tier in ["pretty", "minified", "standard", "lean"]:
            if s["files"][tier]:
                file_links.append(f'<a href="{esc(s["files"][tier])}">{tier[:4]}</a>')

        def kb_cell(val):
            if val > 0:
                return f'<td class="kb">{val:,.1f}</td>'
            return '<td class="kb na">--</td>'

        parts.append(
            f"<tr><td>{i}</td><td><strong>{esc(s['id'])}</strong></td>"
            f"<td>{esc(s['domain'])}</td>"
            f'<td><span class="tag {tag_cls}">{esc(s["size_class"])}</span></td>'
            f'<td class="kb">{s["src_kb"]:,.1f}</td>'
        )
        parts.append(kb_cell(s["sizes"]["minified"]))
        parts.append(kb_cell(s["sizes"]["standard"]))
        parts.append(kb_cell(s["sizes"]["lean"]))
        parts.append(f'<td class="ratio">{ratio}</td>')
        parts.append(f'<td class="files">{" | ".join(file_links)}</td></tr>')
    parts.append("</table>")

    # Tasks
    parts.append("<h3>Tasks</h3>")
    for s in fspecs:
        review = reviews.get(s["id"])
        badge = ""
        if review:
            vcls = "verdict-problem" if review[0] == "PROBLEM" else "verdict-note" if review[0] == "NOTE" else "verdict-warn"
            badge = f' <span class="verdict {vcls}">{review[0]}</span>'

        parts.append(f"<details><summary><strong>{esc(s['id'])}</strong>{badge}</summary>")

        if review:
            ncls = "review-problem" if review[0] == "PROBLEM" else "review-warn" if review[0] == "WARN" else "review-note"
            parts.append(f'<div class="{ncls}">{esc(review[1])}</div>')

        for t in s["tasks"]:
            tid = t["id"]
            desc = t["description"]
            eps = t.get("target_endpoints", [])
            params = t.get("expected_params", {})

            parts.append('<div class="task">')
            parts.append(
                f'<span class="task-id">{esc(tid)}</span>'
                f'<span class="task-desc">{esc(desc)}</span>'
            )
            parts.append('<div class="endpoints">')
            for ep in eps:
                parts.append(f'<span class="ep">{esc(ep)}</span>')
            parts.append("</div>")
            for ep_key, ep_params in params.items():
                short_key = ep_key if len(ep_key) < 60 else ep_key[:57] + "..."
                if ep_params:
                    param_strs = ", ".join(
                        f'<span class="param">{esc(p)}</span>' for p in ep_params
                    )
                    parts.append(
                        f'<div class="params">{esc(short_key)}: {param_strs}</div>'
                    )
                else:
                    parts.append(
                        f'<div class="params">{esc(short_key)}: <em>(no params)</em></div>'
                    )
            parts.append("</div>")
        parts.append("</details>")
    parts.append("</div>")

# Notes summary
parts.append("<h2>Notes</h2>")
parts.append("<table><tr><th>Spec</th><th>Status</th><th>Note</th></tr>")
for sid, (verdict, note) in sorted(
    reviews.items(), key=lambda x: (0 if x[1][0] == "PROBLEM" else 1 if x[1][0] == "WARN" else 2, x[0])
):
    vcls = "verdict-problem" if verdict == "PROBLEM" else "verdict-note" if verdict == "NOTE" else "verdict-warn"
    parts.append(
        f"<tr><td><strong>{esc(sid)}</strong></td>"
        f'<td><span class="verdict {vcls}">{verdict}</span></td>'
        f"<td>{esc(note)}</td></tr>"
    )
parts.append("</table>")

parts.append(
    '<p style="margin-top:32px;color:var(--muted);font-size:13px">'
    "Generated from registry/registry.yaml + registry/manifests/</p>"
)
parts.append("</body></html>")

html = "\n".join(parts)
out = root / "BENCHMARK_SPECS.html"
out.write_text(html, encoding="utf-8")
print(f"Written {len(html):,} bytes to {out}")
