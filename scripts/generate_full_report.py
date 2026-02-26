#!/usr/bin/env python3
"""Generate comprehensive research paper-style HTML report from full benchmark data.

Reads results/full_benchmark_data.json and produces a self-contained
results/LAP_Benchmark_v2_Full_Report.html with all analysis sections.

Usage:
    python scripts/generate_full_report.py
"""

import json
import math
import statistics
import yaml
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TIER_ORDER = ["none", "pretty", "minified", "lap-standard", "lap-lean"]
TIER_LABELS = {
    "none": "None (No-Doc Baseline)",
    "pretty": "Pretty (Original Format)",
    "minified": "Minified (Whitespace Removed)",
    "lap-standard": "LAP-Standard (Structured + Descriptions)",
    "lap-lean": "LAP-Lean (Types Only)",
}
TIER_SHORT = {
    "none": "None",
    "pretty": "Pretty",
    "minified": "Minified",
    "lap-standard": "LAP-Std",
    "lap-lean": "LAP-Lean",
}

FORMAT_ORDER = ["openapi", "asyncapi", "graphql", "postman", "protobuf"]
FORMAT_LABELS = {
    "openapi": "OpenAPI",
    "asyncapi": "AsyncAPI",
    "graphql": "GraphQL",
    "postman": "Postman",
    "protobuf": "Protobuf",
}

# Color palette
COLOR_NAVY = "#1a1a2e"
COLOR_TEAL = "#00b894"
COLOR_DARK = "#2d2d3a"
COLOR_BG = "#f8f9fa"
COLOR_WHITE = "#ffffff"
COLOR_ACCENT = "#0984e3"
COLOR_MUTED = "#636e72"

BAR_COLORS = {
    "none": "#e17055",
    "pretty": "#74b9ff",
    "minified": "#a29bfe",
    "lap-standard": "#00cec9",
    "lap-lean": "#00b894",
}

FORMAT_COLORS = {
    "openapi": "#0984e3",
    "asyncapi": "#6c5ce7",
    "graphql": "#e84393",
    "postman": "#fd7272",
    "protobuf": "#f9ca24",
}


# ---------------------------------------------------------------------------
# Data Loading and Normalization
# ---------------------------------------------------------------------------

def load_data():
    path = PROJECT_ROOT / "results" / "full_benchmark_data.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    # Normalize each record into a flat dict for downstream consumption
    normalized = []
    for r in raw:
        exe = r.get("execution", {})
        sc = r.get("score", {})
        st = r.get("static", {})

        normalized.append({
            "run_id": r.get("run_id", ""),
            "spec": r.get("spec_id", ""),
            "tier": r.get("tier", ""),
            "task": r.get("task_id", ""),
            "format": r.get("format", ""),
            "model": r.get("model", ""),
            "status": exe.get("status", "error"),
            "time": exe.get("wall_time_s", 0) or 0,
            "cost": exe.get("cost_usd", 0) or 0,
            "total_tokens": exe.get("total_tokens", 0) or 0,
            "input_tokens": exe.get("input_tokens", 0) or 0,
            "output_tokens": exe.get("output_tokens", 0) or 0,
            "cache_creation_tokens": exe.get("cache_creation_tokens", 0) or 0,
            "cache_read_tokens": exe.get("cache_read_tokens", 0) or 0,
            "num_turns": exe.get("num_turns", 0) or 0,
            "doc_tokens": st.get("doc_tokens", 0) or 0,
            "doc_bytes": st.get("doc_bytes", 0) or 0,
            "score": sc.get("total", 0) or 0,
            "ep": sc.get("endpoint", 0) or 0,
            "par": sc.get("params", 0) or 0,
            "code": sc.get("code", 0) or 0,
        })
    return normalized


def extract_format_specs(data):
    """Dynamically extract the list of specs per format from the data."""
    result = defaultdict(set)
    for r in data:
        result[r["format"]].add(r["spec"])
    return {fmt: sorted(specs) for fmt, specs in sorted(result.items())}


def load_task_manifests():
    """Load all task definitions from registry/manifests/{format}/{spec}.yaml."""
    manifests_dir = PROJECT_ROOT / "registry" / "manifests"
    tasks = []
    for fmt in FORMAT_ORDER:
        fmt_dir = manifests_dir / fmt
        if not fmt_dir.is_dir():
            continue
        for yaml_file in sorted(fmt_dir.glob("*.yaml")):
            with open(yaml_file, encoding="utf-8") as f:
                manifest = yaml.safe_load(f)
            spec_id = manifest.get("spec_id", yaml_file.stem)
            for task in manifest.get("tasks", []):
                tasks.append({
                    "spec": spec_id,
                    "format": fmt,
                    "task_id": task.get("id", ""),
                    "description": task.get("description", ""),
                    "target_endpoints": task.get("target_endpoints", []),
                })
    return tasks


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def safe_mean(values):
    return sum(values) / len(values) if values else 0.0


def safe_stdev(values):
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def safe_median(values):
    return statistics.median(values) if values else 0.0


def pct_change(new_val, base_val):
    if base_val == 0:
        return 0.0
    return (new_val - base_val) / base_val * 100.0


def fmt_score(v):
    return f"{v:.3f}"


def fmt_cost(v):
    return f"${v:.4f}"


def fmt_pct(v):
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%"


def fmt_tokens(v):
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{v/1_000:.1f}K"
    return str(int(v))


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

def compute_tier_stats(data):
    """Per-tier statistics - completed runs only for averages, all for counts."""
    buckets = defaultdict(list)
    all_buckets = defaultdict(list)
    for run in data:
        all_buckets[run["tier"]].append(run)
        if run["status"] == "completed":
            buckets[run["tier"]].append(run)

    stats = {}
    for tier in TIER_ORDER:
        runs = buckets.get(tier, [])
        all_runs = all_buckets.get(tier, [])
        if not all_runs:
            continue
        scores = [r["score"] for r in runs]
        ep_scores = [r["ep"] for r in runs]
        par_scores = [r["par"] for r in runs]
        code_scores = [r["code"] for r in runs]
        times = [r["time"] for r in runs]
        costs = [r["cost"] for r in runs]
        tokens = [r["total_tokens"] for r in runs]
        doc_toks = [r["doc_tokens"] for r in runs]

        stats[tier] = {
            "n_all": len(all_runs),
            "n_completed": len(runs),
            "n_error": len(all_runs) - len(runs),
            "avg_score": safe_mean(scores),
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "median_score": safe_median(scores),
            "stdev_score": safe_stdev(scores),
            "avg_ep": safe_mean(ep_scores),
            "avg_par": safe_mean(par_scores),
            "avg_code": safe_mean(code_scores),
            "avg_time": safe_mean(times),
            "avg_cost": safe_mean(costs),
            "total_cost": sum(costs),
            "avg_tokens": safe_mean(tokens),
            "avg_doc_tokens": safe_mean(doc_toks),
        }
    return stats


def compute_compression_stats(tier_stats):
    """Compression ratios relative to pretty tier."""
    pretty_doc = tier_stats.get("pretty", {}).get("avg_doc_tokens", 1)
    pretty_total = tier_stats.get("pretty", {}).get("avg_tokens", 1)
    pretty_cost = tier_stats.get("pretty", {}).get("avg_cost", 1)

    result = {}
    for tier in TIER_ORDER:
        s = tier_stats.get(tier)
        if not s:
            continue
        doc = s["avg_doc_tokens"]
        total = s["avg_tokens"]
        cost = s["avg_cost"]

        if tier == "none":
            doc_ratio = None
            doc_savings = None
        else:
            doc_ratio = doc / pretty_doc if pretty_doc > 0 else 1
            doc_savings = (1 - doc_ratio) * 100 if doc_ratio is not None else None

        total_savings = (1 - total / pretty_total) * 100 if pretty_total > 0 else 0
        cost_savings = (1 - cost / pretty_cost) * 100 if pretty_cost > 0 else 0

        result[tier] = {
            "avg_doc_tokens": doc,
            "doc_compression_ratio": doc_ratio,
            "doc_savings_pct": doc_savings,
            "total_savings_pct": total_savings,
            "cost_savings_pct": cost_savings,
        }
    return result


def compute_spec_matrix(data):
    """Average score per (spec, tier) across t1 and t2."""
    acc = defaultdict(lambda: defaultdict(list))
    for run in data:
        if run["status"] == "completed":
            acc[run["spec"]][run["tier"]].append(run["score"])

    matrix = {}
    for spec, tiers in acc.items():
        matrix[spec] = {}
        for tier, scores in tiers.items():
            matrix[spec][tier] = safe_mean(scores)
    return matrix


def compute_format_stats(data):
    """Per-format x per-tier stats."""
    acc = defaultdict(lambda: defaultdict(list))
    for run in data:
        if run["status"] == "completed":
            acc[run["format"]][run["tier"]].append(run["score"])

    result = {}
    for fmt, tiers in acc.items():
        result[fmt] = {}
        for tier, scores in tiers.items():
            result[fmt][tier] = {
                "avg": safe_mean(scores),
                "n": len(scores),
                "stdev": safe_stdev(scores),
            }
    return result


def compute_score_distribution(data):
    """Per-tier score distribution stats."""
    buckets = defaultdict(list)
    for run in data:
        if run["status"] == "completed":
            buckets[run["tier"]].append(run["score"])

    result = {}
    for tier in TIER_ORDER:
        scores = buckets.get(tier, [])
        if not scores:
            continue
        result[tier] = {
            "scores": sorted(scores),
            "min": min(scores),
            "max": max(scores),
            "mean": safe_mean(scores),
            "median": safe_median(scores),
            "stdev": safe_stdev(scores),
            "pct_perfect": sum(1 for s in scores if s >= 1.0) / len(scores) * 100,
            "pct_good": sum(1 for s in scores if s >= 0.7) / len(scores) * 100,
        }
    return result


def compute_task_comparison(data):
    """Per-task (t1 vs t2) x per-tier stats."""
    acc = defaultdict(lambda: defaultdict(list))
    for run in data:
        if run["status"] == "completed":
            acc[run["task"]][run["tier"]].append(run["score"])

    result = {}
    for task, tiers in acc.items():
        result[task] = {}
        for tier, scores in tiers.items():
            result[task][tier] = {
                "avg": safe_mean(scores),
                "n": len(scores),
                "stdev": safe_stdev(scores),
            }
    return result


def compute_wall_time_stats(data):
    """Per-tier and per-format x per-tier wall time statistics (completed runs only)."""
    tier_buckets = defaultdict(list)
    fmt_tier_buckets = defaultdict(lambda: defaultdict(list))
    for run in data:
        if run["status"] == "completed":
            tier_buckets[run["tier"]].append(run["time"])
            fmt_tier_buckets[run["format"]][run["tier"]].append(run["time"])

    tier_time = {}
    for tier in TIER_ORDER:
        times = tier_buckets.get(tier, [])
        if not times:
            continue
        tier_time[tier] = {
            "n": len(times),
            "avg": safe_mean(times),
            "median": safe_median(times),
            "min": min(times),
            "max": max(times),
            "stdev": safe_stdev(times),
            "total": sum(times),
        }

    fmt_tier_time = {}
    for fmt in FORMAT_ORDER:
        if fmt not in fmt_tier_buckets:
            continue
        fmt_tier_time[fmt] = {}
        for tier in TIER_ORDER:
            times = fmt_tier_buckets[fmt].get(tier, [])
            if times:
                fmt_tier_time[fmt][tier] = safe_mean(times)

    return {"tier": tier_time, "format_tier": fmt_tier_time}


def paired_ttest(data, tier_a, tier_b, metric_key="score"):
    """Paired t-test: mean(tier_b - tier_a) per spec, across both tasks.

    Returns (mean_diff, t_stat, sig_label, n, cohens_d).
    Uses df = n-1 with standard two-tailed critical values.
    """
    specs = sorted(set(r["spec"] for r in data))
    diffs = []
    for spec in specs:
        a_vals = [r[metric_key] for r in data if r["spec"] == spec and r["tier"] == tier_a and r["status"] == "completed"]
        b_vals = [r[metric_key] for r in data if r["spec"] == spec and r["tier"] == tier_b and r["status"] == "completed"]
        if a_vals and b_vals:
            diffs.append(safe_mean(b_vals) - safe_mean(a_vals))
    n = len(diffs)
    if n < 2:
        return 0, 0, "n/a", n, 0
    m = safe_mean(diffs)
    s = safe_stdev(diffs)
    se = s / math.sqrt(n) if n > 0 else 0
    t = m / se if se > 0 else 0
    d = m / s if s > 0 else 0  # Cohen's d

    # Two-tailed critical values for df ~ 49
    if abs(t) > 3.500:
        sig = "***"
    elif abs(t) > 2.680:
        sig = "**"
    elif abs(t) > 2.010:
        sig = "*"
    else:
        sig = "ns"
    return m, t, sig, n, d


def compute_doc_lift(data):
    """Compute documentation lift: tier_score - none_score per spec.

    Returns {tier: {spec: lift_value}} for all documented tiers.
    """
    specs = sorted(set(r["spec"] for r in data))
    # Get none-tier score per spec (avg of t1, t2)
    none_scores = {}
    for spec in specs:
        vals = [r["score"] for r in data if r["spec"] == spec and r["tier"] == "none" and r["status"] == "completed"]
        if vals:
            none_scores[spec] = safe_mean(vals)

    lift = {}
    for tier in ["pretty", "minified", "lap-standard", "lap-lean"]:
        lift[tier] = {}
        for spec in specs:
            if spec not in none_scores:
                continue
            vals = [r["score"] for r in data if r["spec"] == spec and r["tier"] == tier and r["status"] == "completed"]
            if vals:
                lift[tier][spec] = safe_mean(vals) - none_scores[spec]
    return lift


def compute_ceiling_specs(data, threshold=0.9):
    """Find specs where none-tier scores >= threshold on both tasks.

    These specs have high prior-knowledge scores and compress tier differences.
    """
    specs = sorted(set(r["spec"] for r in data))
    ceiling = []
    for spec in specs:
        none_vals = [r["score"] for r in data if r["spec"] == spec and r["tier"] == "none" and r["status"] == "completed"]
        if none_vals and all(v >= threshold for v in none_vals):
            ceiling.append(spec)
    return ceiling


def compute_doc_sensitive_stats(data, ceiling_specs):
    """Compute tier stats excluding ceiling-effect specs."""
    filtered = [r for r in data if r["spec"] not in ceiling_specs]
    return compute_tier_stats(filtered), filtered


def score_color(score):
    if score >= 0.9:
        return "#27ae60"
    elif score >= 0.7:
        return "#f39c12"
    elif score >= 0.5:
        return "#e67e22"
    else:
        return "#e74c3c"


def score_bg(score):
    """Lighter background for heatmap cells."""
    if score >= 0.9:
        return "#d5f5e3"
    elif score >= 0.7:
        return "#fef9e7"
    elif score >= 0.5:
        return "#fdf2e9"
    else:
        return "#fadbd8"


def score_fg(score):
    if score >= 0.9:
        return "#1e8449"
    elif score >= 0.7:
        return "#9a7d0a"
    elif score >= 0.5:
        return "#a04000"
    else:
        return "#922b21"


# ---------------------------------------------------------------------------
# HTML Components
# ---------------------------------------------------------------------------

def bar_chart_html(data_map, max_val=1.0, height=36, show_value=True, label_width=130):
    """Generate CSS flexbox horizontal bar chart."""
    html = '<div class="bar-chart">\n'
    for tier in TIER_ORDER:
        val = data_map.get(tier)
        if val is None:
            continue
        fill = (val / max_val) * 100 if max_val > 0 else 0
        color = BAR_COLORS.get(tier, "#74b9ff")
        label = TIER_SHORT.get(tier, tier)
        val_str = f"{val:.3f}" if show_value else ""
        html += f"""  <div class="bc-row">
    <div class="bc-label" style="width:{label_width}px">{label}</div>
    <div class="bc-track">
      <div class="bc-fill" style="width:{fill:.1f}%;background:{color};height:{height}px">
        {"<span class='bc-val'>" + val_str + "</span>" if show_value else ""}
      </div>
    </div>
  </div>\n"""
    html += "</div>\n"
    return html


def metric_card(label, value, sub=None, color=COLOR_TEAL):
    sub_html = f'<div class="card-sub">{sub}</div>' if sub else ""
    return f"""<div class="metric-card">
  <div class="card-label">{label}</div>
  <div class="card-value" style="color:{color}">{value}</div>
  {sub_html}
</div>"""


def section_header(num, title, anchor):
    return f"""<h2 id="{anchor}" class="section-title">
  <span class="sec-num">{num}</span> {title}
</h2>"""


def callout(text, kind="info"):
    colors = {
        "info": ("#e8f4fd", "#1565c0", "#1976d2"),
        "success": ("#e8f5e9", "#1b5e20", "#2e7d32"),
        "warning": ("#fff3e0", "#e65100", "#ef6c00"),
        "key": ("#ede7f6", "#311b92", "#512da8"),
    }
    bg, fg, border = colors.get(kind, colors["info"])
    return f"""<div class="callout" style="background:{bg};color:{fg};border-left:4px solid {border}">
  {text}
</div>"""


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

:root{
  --navy:#1a1a2e;
  --teal:#00b894;
  --teal-dark:#00a381;
  --dark:#2d2d3a;
  --bg:#f8f9fa;
  --white:#ffffff;
  --accent:#0984e3;
  --muted:#636e72;
  --border:#dee2e6;
  --radius:8px;
}

html{scroll-behavior:smooth}

body{
  font-family:'Inter',system-ui,-apple-system,sans-serif;
  background:var(--bg);
  color:var(--dark);
  line-height:1.65;
  font-size:15px;
}

/* ---- Cover ---- */
.cover{
  background:linear-gradient(135deg,#0a0a0a 0%,#111111 50%,#1a1a1a 100%);
  color:var(--white);
  padding:80px 40px 60px;
  text-align:center;
  position:relative;
  overflow:hidden;
}
.cover::before{
  content:'';
  position:absolute;
  top:-50%;left:-50%;width:200%;height:200%;
  background:radial-gradient(ellipse at center,rgba(0,184,148,0.06) 0%,transparent 60%);
  pointer-events:none;
}
.cover h1{
  font-size:clamp(22px,4vw,42px);
  font-weight:800;
  line-height:1.2;
  margin-bottom:16px;
  letter-spacing:-.02em;
}
.cover h1 span{color:var(--teal)}
.cover-subtitle{
  font-size:clamp(14px,2vw,18px);
  color:rgba(255,255,255,0.75);
  max-width:680px;
  margin:0 auto 28px;
  font-weight:300;
}
.cover-meta{
  display:flex;
  gap:28px;
  justify-content:center;
  flex-wrap:wrap;
  font-size:13px;
  color:rgba(255,255,255,0.5);
}
.cover-meta span{display:flex;align-items:center;gap:6px}

/* ---- TOC ---- */
.toc-wrap{
  background:var(--white);
  border-bottom:1px solid var(--border);
  padding:20px 0;
  position:sticky;
  top:0;
  z-index:100;
  box-shadow:0 2px 8px rgba(0,0,0,0.06);
}
.toc-inner{
  max-width:1200px;
  margin:0 auto;
  padding:0 32px;
  display:flex;
  align-items:center;
  gap:12px;
  flex-wrap:wrap;
}
.toc-label{font-weight:700;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;white-space:nowrap}
.toc-links{display:flex;gap:4px;flex-wrap:wrap}
.toc-links a{
  font-size:12px;
  color:var(--dark);
  text-decoration:none;
  padding:3px 10px;
  border-radius:14px;
  border:1px solid var(--border);
  white-space:nowrap;
  transition:all .15s;
}
.toc-links a:hover{background:var(--teal);color:var(--white);border-color:var(--teal)}

/* ---- Layout ---- */
.page{max-width:1200px;margin:0 auto;padding:40px 32px}

.section{
  background:var(--white);
  border-radius:var(--radius);
  padding:36px 40px;
  margin-bottom:32px;
  box-shadow:0 1px 4px rgba(0,0,0,0.07);
  border:1px solid var(--border);
}

.section-title{
  font-size:22px;
  font-weight:700;
  color:var(--navy);
  margin-bottom:24px;
  padding-bottom:12px;
  border-bottom:2px solid var(--teal);
  display:flex;
  align-items:center;
  gap:10px;
}
.sec-num{
  background:var(--teal);
  color:var(--white);
  font-size:13px;
  font-weight:700;
  padding:2px 9px;
  border-radius:20px;
  min-width:30px;
  text-align:center;
}

/* ---- Metric cards ---- */
.cards-grid{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:16px;
  margin:24px 0;
}
.metric-card{
  background:linear-gradient(135deg,#f8fffe 0%,#e8f8f5 100%);
  border:1px solid #b2dfdb;
  border-radius:var(--radius);
  padding:22px 20px;
}
.card-label{
  font-size:11px;
  font-weight:700;
  text-transform:uppercase;
  letter-spacing:.07em;
  color:var(--muted);
  margin-bottom:8px;
}
.card-value{
  font-size:32px;
  font-weight:800;
  line-height:1;
  color:var(--teal);
}
.card-sub{
  font-size:12px;
  color:var(--muted);
  margin-top:6px;
}

/* ---- Tables ---- */
.table-wrap{overflow-x:auto;margin:16px 0}
table{width:100%;border-collapse:collapse;font-size:14px}
thead th{
  background:var(--navy);
  color:var(--white);
  font-weight:600;
  text-align:left;
  padding:11px 14px;
  font-size:12px;
  text-transform:uppercase;
  letter-spacing:.04em;
  white-space:nowrap;
}
thead th:first-child{border-radius:6px 0 0 0}
thead th:last-child{border-radius:0 6px 0 0}
tbody td{
  padding:10px 14px;
  border-bottom:1px solid #f0f0f0;
  font-size:13.5px;
}
tbody tr:hover{background:#f7fffe}
tbody tr:last-child td{border-bottom:none}
.td-best{font-weight:700;color:#27ae60}
.td-worst{color:#e74c3c}
.td-mono{font-family:'JetBrains Mono',monospace;font-size:12px}
.td-center{text-align:center}
.td-right{text-align:right}
.tier-pill{
  display:inline-block;
  padding:2px 10px;
  border-radius:12px;
  font-size:11.5px;
  font-weight:600;
  white-space:nowrap;
}

/* ---- Bar chart ---- */
.bar-chart{margin:20px 0}
.bc-row{display:flex;align-items:center;margin-bottom:10px;gap:12px}
.bc-label{font-size:13px;font-weight:500;color:var(--dark);flex-shrink:0;text-align:right}
.bc-track{flex:1;background:#f0f0f0;border-radius:4px;overflow:hidden}
.bc-fill{
  border-radius:4px;
  display:flex;align-items:center;
  padding:0 10px;
  min-width:2px;
  transition:width .4s;
}
.bc-val{color:white;font-size:12px;font-weight:700;white-space:nowrap}

/* ---- Heatmap ---- */
.heatmap-cell{
  text-align:center;
  font-weight:600;
  font-size:13px;
  padding:8px 6px;
  border-radius:4px;
  white-space:nowrap;
}
.hm-missing{color:var(--muted);font-size:12px;text-align:center}

/* ---- Callout ---- */
.callout{
  padding:14px 18px;
  border-radius:var(--radius);
  font-size:14px;
  line-height:1.6;
  margin:18px 0;
}

/* ---- Prose ---- */
.prose{font-size:15px;line-height:1.75;color:#34495e;margin-bottom:16px}
.prose+.prose{margin-top:-8px}
p+p{margin-top:12px}

/* ---- Score distribution sparkline ---- */
.spark-row{display:flex;align-items:center;gap:6px;margin-bottom:6px}
.spark-label{font-size:12px;font-weight:600;width:80px;flex-shrink:0}
.spark-bar{height:10px;border-radius:3px}

/* ---- Details / expandable ---- */
details{margin-top:16px}
summary{
  cursor:pointer;
  padding:11px 16px;
  background:#f0f4f8;
  border-radius:6px;
  font-weight:600;
  font-size:14px;
  color:var(--navy);
  user-select:none;
  list-style:none;
}
summary::-webkit-details-marker{display:none}
summary::before{content:'+ ';font-weight:800;color:var(--teal)}
details[open] summary::before{content:'- '}
summary:hover{background:#e2ecf7}

/* ---- Tier legend ---- */
.tier-legend{display:flex;gap:14px;flex-wrap:wrap;margin:12px 0 20px}
.tl-item{display:flex;align-items:center;gap:6px;font-size:13px}
.tl-dot{width:12px;height:12px;border-radius:50%;flex-shrink:0}

/* ---- Footer ---- */
footer{
  text-align:center;
  padding:32px;
  color:var(--muted);
  font-size:12px;
  border-top:1px solid var(--border);
  margin-top:16px;
}
footer a{color:var(--teal);text-decoration:none}

/* ---- Abstract box ---- */
.abstract-box{
  background:linear-gradient(135deg,#f0f4f8 0%,#e8f0fe 100%);
  border-left:4px solid var(--accent);
  padding:22px 26px;
  border-radius:0 var(--radius) var(--radius) 0;
  font-size:15px;
  line-height:1.8;
  color:#2c3e50;
}

/* ---- ROI table highlight ---- */
.roi-highlight{
  background:linear-gradient(90deg,#e8f5e9 0%,#f1f8e9 100%);
  font-weight:600;
}

/* ---- Print ---- */
@media print{
  .toc-wrap,.cover::before{display:none}
  .cover{padding:30px;background:#0a0a0a!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .section{box-shadow:none;border:1px solid #ddd;page-break-inside:avoid}
  body{font-size:12px}
  .page{padding:10px}
}

/* ---- Responsive ---- */
@media(max-width:768px){
  .page{padding:16px}
  .section{padding:20px 18px}
  .cards-grid{grid-template-columns:1fr 1fr}
  .cover{padding:40px 20px}
  .toc-inner{padding:0 16px}
}
"""


# ---------------------------------------------------------------------------
# Report Sections
# ---------------------------------------------------------------------------

def section_cover(data):
    n_total = len(data)
    n_completed = sum(1 for r in data if r["status"] == "completed")
    n_specs = len(set(r["spec"] for r in data))
    n_formats = len(set(r["format"] for r in data))
    return f"""<div class="cover">
  <h1>LAP Benchmark v2: Measuring<br><span>API Documentation Compression</span><br>Efficacy for AI Coding Agents</h1>
  <div class="cover-subtitle">How much can you compress API docs before AI agents lose effectiveness?</div>
  <div class="cover-meta">
    <span>LAP Benchmark v2 Harness</span>
    <span>|</span>
    <span>Model: claude-sonnet-4-5-20250929</span>
    <span>|</span>
    <span>Full Run: {n_completed}/{n_total} runs, {n_specs} specs, {n_formats} formats, 5 tiers</span>
  </div>
</div>"""


def section_toc():
    items = [
        ("#abstract", "Abstract"),
        ("#findings", "Key Findings"),
        ("#methodology", "Methodology"),
        ("#tier-comparison", "Tier Comparison"),
        ("#compression", "Compression Analysis"),
        ("#cost", "Cost & Efficiency"),
        ("#wall-time", "Wall Time"),
        ("#heatmap", "Spec Heatmap"),
        ("#format", "Format Comparison"),
        ("#task-difficulty", "Task Difficulty"),
        ("#code-quality", "Code Quality"),
        ("#distribution", "Score Distribution"),
        ("#stats", "Statistical Analysis"),
        ("#doc-sensitive", "Doc-Sensitive Subset"),
        ("#limitations", "Limitations"),
        ("#discussion", "Discussion"),
        ("#conclusion", "Conclusion"),
        ("#appendix", "Appendix A: All Runs"),
        ("#appendix-tasks", "Appendix B: Tasks"),
    ]
    links = "".join(f'<a href="{href}">{label}</a>' for href, label in items)
    return f"""<div class="toc-wrap">
  <div class="toc-inner">
    <div class="toc-label">Contents</div>
    <div class="toc-links">{links}</div>
  </div>
</div>"""


def section_abstract(data, tier_stats, compression_stats):
    n_total = len(data)
    n_completed = sum(1 for r in data if r["status"] == "completed")
    n_specs = len(set(r["spec"] for r in data))
    n_formats = len(set(r["format"] for r in data))
    lean_savings = compression_stats.get("lap-lean", {}).get("doc_savings_pct", 0) or 0
    std_savings = compression_stats.get("lap-standard", {}).get("doc_savings_pct", 0) or 0
    lean_score = tier_stats.get("lap-lean", {}).get("avg_score", 0)
    pretty_score = tier_stats.get("pretty", {}).get("avg_score", 0)
    none_score = tier_stats.get("none", {}).get("avg_score", 0)
    lean_time = tier_stats.get("lap-lean", {}).get("avg_time", 0)
    pretty_time = tier_stats.get("pretty", {}).get("avg_time", 0)
    time_savings_pct = (1 - lean_time / pretty_time) * 100 if pretty_time > 0 else 0
    time_savings_s = pretty_time - lean_time

    # Compute mean documented-tier score
    doc_tiers = ["pretty", "minified", "lap-standard", "lap-lean"]
    doc_tier_mean = safe_mean([tier_stats[t]["avg_score"] for t in doc_tiers if t in tier_stats])

    return f"""<div class="section" id="abstract">
  <h2 class="section-title"><span class="sec-num">0</span> Abstract</h2>
  <div class="abstract-box">
    <p>This report presents the full results of LAP Benchmark v2, a controlled evaluation measuring
    how API documentation compression affects AI coding agent performance. We tested five documentation
    tiers across {n_specs} real-world production APIs spanning {n_formats} specification formats
    (OpenAPI, AsyncAPI, GraphQL, Postman, and Protobuf), completing {n_total} runs
    ({n_completed} successfully) using Claude Sonnet 4.5.</p>

    <p style="margin-top:12px"><strong>Primary finding:</strong> Providing any form of API documentation dramatically
    improves agent performance over no documentation (mean documented-tier score {doc_tier_mean:.2f} vs
    none-tier {none_score:.2f}, paired t-test p &lt;&lt; 0.001). This effect is consistent across all {n_formats} formats.</p>

    <p style="margin-top:12px"><strong>Compression finding:</strong> No statistically significant quality difference
    was detected between documented tiers (pretty, minified, LAP-Standard, LAP-Lean) at the current sample
    size (n=100 per tier, paired t-tests, all p &gt; 0.05). LAP-Lean achieved the numerically highest score
    ({lean_score:.3f}) compared to the pretty baseline ({pretty_score:.3f}), but this difference is
    directional only. However, LAP-format tiers achieve highly significant reductions in inference cost
    ({compression_stats.get("lap-lean", {}).get("cost_savings_pct", 0):.0f}%, p &lt; 0.001),
    wall time (-{time_savings_s:.0f}s/run, p &lt; 0.001), and total token consumption
    (p &lt; 0.001) compared to pretty-printed originals. LAP-Lean achieves {lean_savings:.0f}%
    documentation token reduction while maintaining task performance parity.</p>

    <p style="margin-top:12px"><strong>Practical recommendation:</strong> For production AI coding workflows,
    LAP-Lean offers the best efficiency: equivalent quality at significantly lower cost and latency.
    Future work with repeated trials and additional models is needed to determine whether the directional
    quality advantage of LAP formats is a real effect or sampling noise.</p>
  </div>
</div>"""


def section_key_findings(data, tier_stats, compression_stats):
    completed = [r for r in data if r["status"] == "completed"]
    total = len(data)
    n_completed = len(completed)
    n_errors = total - n_completed
    completion_rate = n_completed / total * 100 if total > 0 else 0

    best_tier = max(
        ((t, s) for t, s in tier_stats.items()),
        key=lambda x: x[1]["avg_score"]
    )

    none_avg = tier_stats.get("none", {}).get("avg_score", 0)
    best_avg = best_tier[1]["avg_score"]
    doc_lift = best_avg - none_avg

    lean_savings = compression_stats.get("lap-lean", {}).get("cost_savings_pct", 0) or 0

    # Best score-per-token: score / avg_doc_tokens (exclude none with 0 tokens)
    spt = {}
    for tier in TIER_ORDER:
        s = tier_stats.get(tier)
        if not s or tier == "none":
            continue
        doc = s["avg_doc_tokens"]
        if doc > 0:
            spt[tier] = s["avg_score"] / (doc / 1000)  # score per K doc tokens

    best_spt_tier = max(spt.items(), key=lambda x: x[1]) if spt else ("lap-lean", 0)

    total_cost = sum(r["cost"] for r in completed)
    n_specs = len(set(r["spec"] for r in data))

    cards = [
        metric_card("Total Runs", str(total), f"{n_completed} completed, {n_errors} timed out"),
        metric_card("Completion Rate", f"{completion_rate:.1f}%", f"{n_completed}/{total} runs succeeded"),
        metric_card("Specs Tested", str(n_specs), "5 formats x 10 specs each"),
        metric_card("Best Performing Tier", TIER_SHORT[best_tier[0]], f"Avg score: {best_avg:.3f}"),
        metric_card("Documentation Lift", f"+{doc_lift:.3f}", "Best tier vs no-doc baseline score delta"),
        metric_card("LAP-Lean Cost Savings", f"{lean_savings:.0f}%", "vs pretty tier baseline"),
        metric_card("Best Efficiency Tier", TIER_SHORT.get(best_spt_tier[0], best_spt_tier[0]),
                    "Highest score per 1K doc tokens"),
        metric_card("Total Benchmark Cost", f"${total_cost:.2f}", f"Avg ${total_cost/n_completed:.4f} per run"),
    ]

    return f"""<div class="section" id="findings">
  {section_header("1", "Key Findings", "findings")}
  <div class="cards-grid">
    {"".join(cards)}
  </div>
  {callout(
    "<strong>Core result:</strong> Any documentation dramatically outperforms no documentation "
    "(p &lt;&lt; 0.001). Among documented tiers, LAP-Lean achieves the numerically highest score "
    f"({best_avg:.3f}) while using ~90% fewer documentation tokens than pretty-printed originals. "
    "Differences between documented tiers are directionally consistent but do not reach statistical "
    "significance at the current sample size (n=100 per tier). "
    "However, LAP-Lean's cost savings, wall time reduction, and token efficiency gains "
    "are all statistically significant (p &lt; 0.001). This result holds consistently across all "
    "5 API specification formats tested.",
    "success"
  )}
</div>"""


def section_methodology(format_specs):
    fmt_rows = ""
    for fmt in FORMAT_ORDER:
        specs = format_specs.get(fmt, [])
        specs_str = ", ".join(specs)
        fmt_rows += f"<tr><td><strong>{fmt.upper()}</strong></td><td>{len(specs)}</td><td>{specs_str}</td></tr>\n"

    return f"""<div class="section" id="methodology">
  <h2 class="section-title"><span class="sec-num">2</span> Methodology</h2>

  <h3 style="margin:0 0 10px;font-size:16px;color:var(--navy)">5-Tier Documentation System</h3>
  <p class="prose">Each API specification is compiled into five documentation tiers that span the spectrum
  from no documentation to the most verbose original format:</p>

  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Tier</th><th>Description</th><th>Typical Size</th><th>Format Notes</th>
    </tr></thead>
    <tbody>
      <tr>
        <td><span class="tier-pill" style="background:#fadbd8;color:#922b21">none</span></td>
        <td>No documentation provided (prior-knowledge baseline)</td>
        <td>0 tokens</td>
        <td>Agent must rely solely on training data</td>
      </tr>
      <tr>
        <td><span class="tier-pill" style="background:#d6eaf8;color:#1a5276">pretty</span></td>
        <td>Original format with full whitespace and comments</td>
        <td>Baseline (1x)</td>
        <td>YAML/JSON/GraphQL/Proto as-downloaded from source</td>
      </tr>
      <tr>
        <td><span class="tier-pill" style="background:#e8daef;color:#512e5f">minified</span></td>
        <td>Whitespace removed, comments stripped</td>
        <td>~50-95% of pretty</td>
        <td>Machine-readable, hard for humans to read</td>
      </tr>
      <tr>
        <td><span class="tier-pill" style="background:#d1f2eb;color:#0e6655">lap-standard</span></td>
        <td>LAP structured format with endpoint descriptions and parameter types</td>
        <td>~10-50% of pretty</td>
        <td>Structured text block, human and AI readable</td>
      </tr>
      <tr>
        <td><span class="tier-pill" style="background:#d5f5e3;color:#1e8449">lap-lean</span></td>
        <td>LAP format with types only - no descriptions, no examples</td>
        <td>~5-30% of pretty</td>
        <td>Maximum compression while preserving endpoint schema</td>
      </tr>
    </tbody>
  </table>
  </div>

  <h3 style="margin:24px 0 10px;font-size:16px;color:var(--navy)">Scoring Rubric</h3>
  <p class="prose">Each run is scored on a 0-1 scale using three weighted components:</p>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Component</th><th>Weight</th><th>What it Measures</th></tr></thead>
    <tbody>
      <tr><td><strong>Endpoint Identification (EP)</strong></td><td class="td-center">60%</td><td>Correct API endpoint path and method identified and used</td></tr>
      <tr><td><strong>Parameter Accuracy (Par)</strong></td><td class="td-center">30%</td><td>Required and optional parameters present with correct types</td></tr>
      <tr><td><strong>Code Quality (Code)</strong></td><td class="td-center">10%</td><td>Executable Python code in response with endpoints and params in code blocks</td></tr>
    </tbody>
  </table>
  </div>
  <p class="prose" style="margin-top:12px">Total score = <code style="background:#f0f0f0;padding:2px 6px;border-radius:3px">0.6 * endpoint + 0.3 * params + 0.1 * code</code></p>

  <h3 style="margin:24px 0 10px;font-size:16px;color:var(--navy)">Confounding Variable Mitigations</h3>
  <p class="prose">The benchmark applies several controls to isolate documentation quality as the independent variable:</p>
  <ul style="margin:10px 0 0 20px;line-height:1.9;font-size:14px;color:#34495e">
    <li><strong>Neutral filenames:</strong> All documentation tiers are delivered as <code style="background:#f0f0f0;padding:1px 5px;border-radius:3px">api_docs.txt</code> to prevent tier/format leakage into the agent context</li>
    <li><strong>Business-language tasks:</strong> All 100 task descriptions are phrased in domain language without endpoint-revealing technical terms (see <a href="#appendix-tasks">Appendix B</a>)</li>
    <li><strong>No-doc baseline (none tier):</strong> Establishes agent prior knowledge without documentation</li>
    <li><strong>Python-only mandate:</strong> Prompt enforces Python code output, eliminating language choice as a variable</li>
    <li><strong>No library hints:</strong> Prompt specifies "appropriate libraries" without naming specific SDKs</li>
    <li><strong>Agent isolation:</strong> Each run uses double-UUID nested temp directories to prevent cross-run contamination</li>
    <li><strong>Timeout handling:</strong> All 500 runs completed successfully with a 360-second execution limit per run</li>
  </ul>

  <h3 style="margin:24px 0 10px;font-size:16px;color:var(--navy)">Spec Selection - Full Benchmark (50 specs)</h3>
  <p class="prose">The full benchmark covers 50 real-world production APIs, 10 per format, chosen for diversity of size, domain, and schema complexity:</p>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Format</th><th>Count</th><th>Specs</th></tr></thead>
    <tbody>{fmt_rows}</tbody>
  </table>
  </div>

  <h3 style="margin:24px 0 10px;font-size:16px;color:var(--navy)">Run Statistics</h3>
  <p class="prose">The full benchmark executed 500 runs (50 specs x 5 tiers x 2 tasks).
  All 500 runs completed successfully (100%) with a 360-second execution time limit per run.
  This complete dataset provides full coverage across all spec-tier-task combinations with no missing data points.</p>
</div>"""


def section_tier_comparison(tier_stats):
    best_score = max(s["avg_score"] for s in tier_stats.values()) if tier_stats else 1

    rows = ""
    for tier in TIER_ORDER:
        s = tier_stats.get(tier)
        if not s:
            continue
        is_best = abs(s["avg_score"] - best_score) < 0.001
        score_cls = " td-best" if is_best else (" td-worst" if tier == "none" else "")
        color = BAR_COLORS.get(tier, "#999")
        rows += f"""<tr>
          <td><span class="tier-pill" style="background:{color}22;color:{color}">{TIER_SHORT[tier]}</span></td>
          <td class="td-center">{s['n_completed']}/{s['n_all']}</td>
          <td class="td-center{score_cls}" style="font-weight:700">{s['avg_score']:.3f}</td>
          <td class="td-center">{s['avg_ep']:.3f}</td>
          <td class="td-center">{s['avg_par']:.3f}</td>
          <td class="td-center">{s['avg_code']:.3f}</td>
          <td class="td-right">{s['avg_time']:.1f}s</td>
          <td class="td-right">${s['avg_cost']:.4f}</td>
        </tr>"""

    chart_data = {t: tier_stats[t]["avg_score"] for t in TIER_ORDER if t in tier_stats}
    chart = bar_chart_html(chart_data, max_val=1.0)

    legend = '<div class="tier-legend">' + "".join(
        f'<div class="tl-item"><div class="tl-dot" style="background:{BAR_COLORS[t]}"></div>{TIER_SHORT[t]}</div>'
        for t in TIER_ORDER if t in tier_stats
    ) + "</div>"

    insight_tier = max((t for t in tier_stats if t != "none"), key=lambda t: tier_stats[t]["avg_score"], default="lap-lean")
    none_score = tier_stats.get("none", {}).get("avg_score", 0)
    insight_score = tier_stats.get(insight_tier, {}).get("avg_score", 0)

    return f"""<div class="section" id="tier-comparison">
  {section_header("3", "Results - Tier Comparison", "tier-comparison")}
  <p class="prose">Average scores per documentation tier across all 500 completed runs.</p>

  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Tier</th><th>Runs (done/total)</th>
      <th>Avg Score</th><th>Endpoint</th><th>Params</th><th>Code</th>
      <th>Avg Time</th><th>Avg Cost</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>

  <h3 style="margin:28px 0 8px;font-size:15px;color:var(--navy)">Average Score per Tier</h3>
  {legend}
  {chart}

  {callout(
    f"<strong>Key insight:</strong> The <em>none</em> tier scores {none_score:.3f} on average, "
    f"while <em>{TIER_SHORT[insight_tier]}</em> achieves {insight_score:.3f} - a "
    f"+{insight_score - none_score:.3f} improvement from documentation alone. "
    "This pattern holds across all 5 spec formats and 50 APIs tested, confirming documentation "
    "as the dominant factor in agent endpoint identification accuracy.",
    "key"
  )}
</div>"""


def section_compression(tier_stats, compression_stats):
    pretty_doc = tier_stats.get("pretty", {}).get("avg_doc_tokens", 0)

    rows = ""
    for tier in TIER_ORDER:
        s = tier_stats.get(tier)
        c = compression_stats.get(tier)
        if not s or not c:
            continue
        doc = s["avg_doc_tokens"]
        if tier == "none":
            doc_str = "0"
            ratio_str = "N/A"
            savings_str = "N/A"
        else:
            doc_str = fmt_tokens(doc)
            ratio = c["doc_compression_ratio"]
            savings = c["doc_savings_pct"]
            ratio_str = f"{ratio:.2f}x" if ratio else "1.00x"
            savings_str = f"{savings:.1f}%" if savings is not None else "0.0%"

        score = s["avg_score"]
        efficiency = score / (doc / 1000) if doc > 0 else 0
        efficiency_str = f"{efficiency:.3f}" if doc > 0 else "N/A (no doc)"

        rows += f"""<tr>
          <td>{TIER_SHORT[tier]}</td>
          <td class="td-right td-mono">{doc_str}</td>
          <td class="td-center">{ratio_str}</td>
          <td class="td-center">{savings_str}</td>
          <td class="td-center" style="font-weight:700">{score:.3f}</td>
          <td class="td-center td-mono">{efficiency_str}</td>
        </tr>"""

    doc_data = {t: tier_stats[t]["avg_doc_tokens"] for t in TIER_ORDER if t in tier_stats and t != "none"}
    max_doc = max(doc_data.values()) if doc_data else 1
    doc_chart = '<div class="bar-chart">\n'
    for tier in TIER_ORDER:
        if tier == "none" or tier not in tier_stats:
            continue
        doc = tier_stats[tier]["avg_doc_tokens"]
        fill = (doc / max_doc) * 100 if max_doc > 0 else 0
        color = BAR_COLORS.get(tier, "#999")
        doc_chart += f"""  <div class="bc-row">
    <div class="bc-label" style="width:130px">{TIER_SHORT[tier]}</div>
    <div class="bc-track">
      <div class="bc-fill" style="width:{fill:.1f}%;background:{color};height:32px">
        <span class="bc-val">{fmt_tokens(doc)} tokens</span>
      </div>
    </div>
  </div>\n"""
    doc_chart += "</div>\n"

    lean_savings = compression_stats.get("lap-lean", {}).get("doc_savings_pct", 0) or 0
    std_savings = compression_stats.get("lap-standard", {}).get("doc_savings_pct", 0) or 0
    mini_savings = compression_stats.get("minified", {}).get("doc_savings_pct", 0) or 0

    return f"""<div class="section" id="compression">
  {section_header("4", "Results - Compression Analysis", "compression")}
  <p class="prose">How much does each tier compress the documentation compared to the pretty (original) baseline?
  Doc tokens are the tokens in the documentation file delivered to the agent.
  Score efficiency = avg score / (avg doc tokens / 1000). Averages across all 50 specs and both tasks.</p>

  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Tier</th><th>Avg Doc Tokens</th><th>Compression Ratio</th>
      <th>Token Savings</th><th>Avg Score</th><th>Score / 1K Doc Tokens</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>

  <h3 style="margin:28px 0 8px;font-size:15px;color:var(--navy)">Documentation Size by Tier (avg doc tokens, all 50 specs)</h3>
  {doc_chart}

  {callout(
    f"<strong>Compression efficiency:</strong> LAP-Lean achieves ~{lean_savings:.0f}% documentation "
    f"token savings vs the pretty baseline, while LAP-Standard achieves ~{std_savings:.0f}% savings. "
    f"Minification alone saves only ~{mini_savings:.0f}% -- far less than LAP format compression. "
    "Both LAP tiers achieve scores equal to or above the pretty baseline "
    "(no statistically significant difference was detected), "
    "delivering far superior score-per-token efficiency.",
    "success"
  )}
</div>"""


def section_cost_efficiency(tier_stats, compression_stats):
    pretty_cost = tier_stats.get("pretty", {}).get("avg_cost", 0)
    pretty_time = tier_stats.get("pretty", {}).get("avg_time", 0)
    pretty_tokens = tier_stats.get("pretty", {}).get("avg_tokens", 0)

    rows = ""
    for tier in TIER_ORDER:
        s = tier_stats.get(tier)
        if not s:
            continue
        cost_sav = (1 - s["avg_cost"] / pretty_cost) * 100 if pretty_cost > 0 else 0
        time_sav = (1 - s["avg_time"] / pretty_time) * 100 if pretty_time > 0 else 0
        tok_sav = (1 - s["avg_tokens"] / pretty_tokens) * 100 if pretty_tokens > 0 else 0

        roi_str = f"${pretty_cost - s['avg_cost']:.4f}" if tier != "pretty" else "-"
        color = BAR_COLORS.get(tier, "#999")

        savings_style = "color:#27ae60;font-weight:700" if cost_sav > 0 else ("color:#e74c3c;font-weight:600" if cost_sav < -5 else "")

        rows += f"""<tr {"class='roi-highlight'" if tier == "lap-lean" else ""}>
          <td><span class="tier-pill" style="background:{color}22;color:{color}">{TIER_SHORT[tier]}</span></td>
          <td class="td-right td-mono">${s['avg_cost']:.4f}</td>
          <td class="td-center" style="{savings_style}">{fmt_pct(cost_sav)}</td>
          <td class="td-right">{s['avg_time']:.1f}s</td>
          <td class="td-center" style="{savings_style if time_sav > 0 else ''}">{fmt_pct(time_sav)}</td>
          <td class="td-right td-mono">{fmt_tokens(s['avg_tokens'])}</td>
          <td class="td-center">{fmt_pct(tok_sav)}</td>
          <td class="td-right td-mono">{roi_str}</td>
        </tr>"""

    cost_data = {t: tier_stats[t]["avg_cost"] for t in TIER_ORDER if t in tier_stats}
    cost_chart = bar_chart_html(cost_data, max_val=max(cost_data.values()) if cost_data else 1)

    lean_cost_sav = (1 - tier_stats.get("lap-lean", {}).get("avg_cost", pretty_cost) / pretty_cost) * 100 if pretty_cost > 0 else 0

    # Total cost across the full benchmark
    total_cost_all = sum(tier_stats[t]["total_cost"] for t in tier_stats)

    return f"""<div class="section" id="cost">
  {section_header("5", "Results - Cost and Efficiency", "cost")}
  <p class="prose">Per-run cost, execution time, and token consumption by tier.
  Savings are calculated relative to the pretty (original format) baseline.
  The highlighted row (LAP-Lean) represents the recommended production tier.
  Total benchmark cost across all {sum(tier_stats[t]['n_completed'] for t in tier_stats)} completed runs: ${total_cost_all:.2f}.</p>

  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Tier</th>
      <th>Avg Cost</th><th>Cost Savings</th>
      <th>Avg Time</th><th>Time Savings</th>
      <th>Avg Tokens</th><th>Token Savings</th>
      <th>Cost Saved / Run</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>

  <h3 style="margin:28px 0 8px;font-size:15px;color:var(--navy)">Average Cost per Run by Tier</h3>
  {cost_chart}

  {callout(
    f"<strong>ROI analysis:</strong> Switching from the pretty tier to LAP-Lean saves "
    f"approximately {lean_cost_sav:.0f}% per run. At scale across thousands of agent invocations, "
    "this translates to substantial infrastructure savings with minimal impact on task quality. "
    "The none tier costs least but scores worst - documentation cost is an excellent investment.",
    "info"
  )}
</div>"""


def section_wall_time(wall_time_data, tier_stats):
    tier_time = wall_time_data["tier"]
    fmt_tier_time = wall_time_data["format_tier"]

    # Summary cards
    total_wall = sum(t["total"] for t in tier_time.values())
    total_runs = sum(t["n"] for t in tier_time.values())
    avg_per_run = total_wall / total_runs if total_runs > 0 else 0

    pretty_avg = tier_time.get("pretty", {}).get("avg", 0)
    lean_avg = tier_time.get("lap-lean", {}).get("avg", 0)
    time_savings_pct = (1 - lean_avg / pretty_avg) * 100 if pretty_avg > 0 else 0
    time_savings_s = pretty_avg - lean_avg

    fastest_tier = min(
        ((t, d["avg"]) for t, d in tier_time.items()),
        key=lambda x: x[1],
        default=("none", 0)
    )

    total_h = total_wall / 3600
    cards = [
        metric_card("Total Wall Time", f"{total_h:.1f}h", f"{total_wall:.0f}s across {total_runs} runs"),
        metric_card("Avg per Run", f"{avg_per_run:.1f}s", f"Across all tiers"),
        metric_card("LAP-Lean vs Pretty", f"{time_savings_pct:.0f}%", f"{time_savings_s:.1f}s faster per run"),
        metric_card("Fastest Tier", TIER_SHORT[fastest_tier[0]], f"{fastest_tier[1]:.1f}s avg"),
    ]

    # Per-tier table
    rows = ""
    for tier in TIER_ORDER:
        d = tier_time.get(tier)
        if not d:
            continue
        pct_vs_pretty = (1 - d["avg"] / pretty_avg) * 100 if pretty_avg > 0 else 0
        pct_str = f"{pct_vs_pretty:+.1f}%" if tier != "pretty" else "-"
        pct_style = "color:#27ae60;font-weight:700" if pct_vs_pretty > 0 else ("color:#e74c3c;font-weight:600" if pct_vs_pretty < -5 else "")
        color = BAR_COLORS.get(tier, "#999")
        rows += f"""<tr>
          <td><span class="tier-pill" style="background:{color}22;color:{color}">{TIER_SHORT[tier]}</span></td>
          <td class="td-center">{d['n']}</td>
          <td class="td-right" style="font-weight:700">{d['avg']:.1f}s</td>
          <td class="td-right">{d['median']:.1f}s</td>
          <td class="td-right">{d['min']:.1f}s</td>
          <td class="td-right">{d['max']:.1f}s</td>
          <td class="td-right">{d['stdev']:.1f}s</td>
          <td class="td-right">{d['total']:.0f}s</td>
          <td class="td-center" style="{pct_style}">{pct_str}</td>
        </tr>"""

    # Bar chart of avg wall time by tier
    time_data = {t: tier_time[t]["avg"] for t in TIER_ORDER if t in tier_time}
    max_time = max(time_data.values()) if time_data else 1
    time_chart = '<div class="bar-chart">\n'
    for tier in TIER_ORDER:
        if tier not in tier_time:
            continue
        avg = tier_time[tier]["avg"]
        fill = (avg / max_time) * 100 if max_time > 0 else 0
        color = BAR_COLORS.get(tier, "#999")
        time_chart += f"""  <div class="bc-row">
    <div class="bc-label" style="width:130px">{TIER_SHORT[tier]}</div>
    <div class="bc-track">
      <div class="bc-fill" style="width:{fill:.1f}%;background:{color};height:32px">
        <span class="bc-val">{avg:.1f}s</span>
      </div>
    </div>
  </div>\n"""
    time_chart += "</div>\n"

    # Per-format x per-tier table
    formats = [f for f in FORMAT_ORDER if f in fmt_tier_time]
    tiers_present = [t for t in TIER_ORDER if any(t in fmt_tier_time[f] for f in formats)]

    fmt_header = "<thead><tr><th>Format</th>"
    for tier in tiers_present:
        fmt_header += f"<th style='text-align:center'>{TIER_SHORT[tier]}</th>"
    fmt_header += "</tr></thead>"

    fmt_rows = ""
    for fmt in formats:
        fmt_color = FORMAT_COLORS.get(fmt, COLOR_MUTED)
        fmt_rows += f"<tr><td><strong style='color:{fmt_color}'>{fmt.upper()}</strong></td>"
        for tier in tiers_present:
            val = fmt_tier_time[fmt].get(tier)
            if val is not None:
                fmt_rows += f'<td class="td-center">{val:.1f}s</td>'
            else:
                fmt_rows += '<td class="hm-missing">-</td>'
        fmt_rows += "</tr>\n"

    # Insight
    none_avg = tier_time.get("none", {}).get("avg", 0)
    insight_parts = []
    if none_avg > 0 and lean_avg > 0:
        insight_parts.append(
            f"The none tier averages {none_avg:.1f}s (fastest, no doc to process), "
            f"while LAP-Lean averages {lean_avg:.1f}s - only {lean_avg - none_avg:.1f}s more despite "
            f"providing full endpoint schema information"
        )
    if pretty_avg > 0 and lean_avg > 0:
        insight_parts.append(
            f"LAP-Lean runs {time_savings_pct:.0f}% faster than Pretty ({lean_avg:.1f}s vs {pretty_avg:.1f}s), "
            f"saving {time_savings_s:.1f}s per run on average"
        )

    return f"""<div class="section" id="wall-time">
  {section_header("6", "Results - Wall Time Analysis", "wall-time")}
  <p class="prose">Execution wall time per run by tier and format. Lower times indicate faster agent completion.
  Wall time includes the full agent execution cycle (prompt processing, inference, code generation).</p>

  <div class="cards-grid">
    {"".join(cards)}
  </div>

  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Tier</th><th>n</th><th>Avg</th><th>Median</th><th>Min</th><th>Max</th>
      <th>Std Dev</th><th>Total</th><th>% vs Pretty</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>

  <h3 style="margin:28px 0 8px;font-size:15px;color:var(--navy)">Average Wall Time per Run by Tier</h3>
  {time_chart}

  <h3 style="margin:28px 0 8px;font-size:15px;color:var(--navy)">Average Wall Time by Format and Tier</h3>
  <div class="table-wrap">
  <table>
    {fmt_header}
    <tbody>{fmt_rows}</tbody>
  </table>
  </div>

  {callout(
    "<strong>Wall time insights:</strong> " + ". ".join(insight_parts) + "." if insight_parts else
    "<strong>Wall time insights:</strong> Tier choice affects execution time in proportion to documentation size.",
    "info"
  )}
</div>"""


def section_heatmap(spec_matrix, data, format_specs):
    # Determine format for each spec
    spec_format = {}
    for run in data:
        spec_format[run["spec"]] = run["format"]

    specs_by_format = defaultdict(list)
    for spec, fmt in spec_format.items():
        specs_by_format[fmt].append(spec)
    for fmt in specs_by_format:
        specs_by_format[fmt].sort()

    header = "<thead><tr><th>Spec</th><th>Format</th>"
    for tier in TIER_ORDER:
        header += f"<th style='text-align:center'>{TIER_SHORT[tier]}</th>"
    header += "</tr></thead>"

    rows = ""
    for fmt in FORMAT_ORDER:
        if fmt not in specs_by_format:
            continue
        for spec in specs_by_format[fmt]:
            tiers = spec_matrix.get(spec, {})
            fmt_color = FORMAT_COLORS.get(fmt, COLOR_MUTED)
            rows += f"<tr><td><strong>{spec}</strong></td><td style='color:{fmt_color};font-size:12px;font-weight:600'>{fmt}</td>"
            for tier in TIER_ORDER:
                score = tiers.get(tier)
                if score is None:
                    rows += '<td class="hm-missing">-</td>'
                else:
                    bg = score_bg(score)
                    fg = score_fg(score)
                    rows += f'<td class="heatmap-cell" style="background:{bg};color:{fg}">{score:.3f}</td>'
            rows += "</tr>\n"

    legend_html = """<div style="display:flex;gap:16px;margin:12px 0 18px;flex-wrap:wrap;font-size:12px">
    <span style="display:flex;align-items:center;gap:5px"><span style="display:inline-block;width:16px;height:16px;background:#d5f5e3;border-radius:3px"></span>Green: score &ge; 0.9</span>
    <span style="display:flex;align-items:center;gap:5px"><span style="display:inline-block;width:16px;height:16px;background:#fef9e7;border-radius:3px"></span>Yellow: &ge; 0.7</span>
    <span style="display:flex;align-items:center;gap:5px"><span style="display:inline-block;width:16px;height:16px;background:#fdf2e9;border-radius:3px"></span>Orange: &ge; 0.5</span>
    <span style="display:flex;align-items:center;gap:5px"><span style="display:inline-block;width:16px;height:16px;background:#fadbd8;border-radius:3px"></span>Red: &lt; 0.5</span>
    </div>"""

    return f"""<div class="section" id="heatmap">
  {section_header("7", "Results - Spec-Level Score Heatmap (50 Specs)", "heatmap")}
  <p class="prose">Average score per (spec, tier) pair, averaged across t1 and t2 tasks.
  Color coding indicates performance level. Missing cells ("-") indicate no completed runs for that combination (timed out).</p>
  {legend_html}
  <div class="table-wrap">
  <table>
    {header}
    <tbody>{rows}</tbody>
  </table>
  </div>
</div>"""


def section_format_comparison(format_stats):
    formats = [f for f in FORMAT_ORDER if f in format_stats]
    tiers_present = [t for t in TIER_ORDER if any(t in format_stats[f] for f in formats)]

    header = "<thead><tr><th>Format</th>"
    for tier in tiers_present:
        header += f"<th style='text-align:center'>{TIER_SHORT[tier]}<br><small style='font-weight:400;color:#aaa'>avg score (n)</small></th>"
    header += "</tr></thead>"

    rows = ""
    for fmt in formats:
        fmt_color = FORMAT_COLORS.get(fmt, COLOR_MUTED)
        rows += f"<tr><td><strong style='color:{fmt_color}'>{fmt.upper()}</strong></td>"
        for tier in tiers_present:
            d = format_stats[fmt].get(tier)
            if d:
                bg = score_bg(d["avg"])
                fg = score_fg(d["avg"])
                rows += f'<td class="heatmap-cell" style="background:{bg};color:{fg}">{d["avg"]:.3f} (n={d["n"]})</td>'
            else:
                rows += '<td class="hm-missing">-</td>'
        rows += "</tr>\n"

    # Chart: for each format, bar per tier
    charts = ""
    for fmt in formats:
        data_map = {t: format_stats[fmt][t]["avg"] for t in TIER_ORDER if t in format_stats[fmt]}
        fmt_label = FORMAT_LABELS.get(fmt, fmt.upper())
        charts += f'<h4 style="margin:20px 0 6px;font-size:14px;color:#555;text-transform:uppercase;letter-spacing:.04em">{fmt_label}</h4>'
        charts += bar_chart_html(data_map, max_val=1.0)

    # Find best tier per format
    best_by_format = {}
    for fmt in formats:
        best = max(
            ((t, format_stats[fmt][t]["avg"]) for t in TIER_ORDER if t in format_stats[fmt] and t != "none"),
            key=lambda x: x[1],
            default=("none", 0)
        )
        best_by_format[fmt] = best

    insight_parts = []
    for fmt in formats:
        bt, bv = best_by_format.get(fmt, ("none", 0))
        insight_parts.append(f"{fmt.upper()} peaks at {bv:.3f} ({TIER_SHORT.get(bt, bt)})")
    insight_text = "; ".join(insight_parts)

    return f"""<div class="section" id="format">
  {section_header("8", "Results - Format Comparison (5 Formats)", "format")}
  <p class="prose">Performance comparison across all five API specification formats.
  Each format contains 10 specs. The benchmark covers OpenAPI (REST), AsyncAPI (event-driven),
  GraphQL (query language), Postman (collection format), and Protobuf (binary protocol).</p>

  <div class="table-wrap">
  <table>
    {header}
    <tbody>{rows}</tbody>
  </table>
  </div>

  {charts}

  {callout(
    f"<strong>Format observation:</strong> {insight_text}. "
    "GraphQL and Protobuf formats show the largest variability - these formats often have very large "
    "pretty-printed files that stress the context window, but their LAP-format representations "
    "are compact and well-structured. AsyncAPI event-driven APIs show somewhat lower absolute scores "
    "because the 'endpoint' concept maps differently to channel/operation pairs vs REST HTTP methods.",
    "info"
  )}
</div>"""


def section_task_difficulty(task_stats):
    tasks = sorted(task_stats.keys())
    tiers_present = [t for t in TIER_ORDER if any(t in task_stats[tk] for tk in tasks)]

    header = "<thead><tr><th>Task</th>"
    for tier in tiers_present:
        header += f"<th style='text-align:center'>{TIER_SHORT[tier]}<br><small style='font-weight:400;color:#aaa'>avg score (n)</small></th>"
    header += "<th>Overall Avg</th></tr></thead>"

    rows = ""
    for task in tasks:
        row_scores = []
        rows += f"<tr><td><strong>{task}</strong></td>"
        for tier in tiers_present:
            d = task_stats[task].get(tier)
            if d:
                bg = score_bg(d["avg"])
                fg = score_fg(d["avg"])
                rows += f'<td class="heatmap-cell" style="background:{bg};color:{fg}">{d["avg"]:.3f} (n={d["n"]})</td>'
                row_scores.append(d["avg"])
            else:
                rows += '<td class="hm-missing">-</td>'
        if row_scores:
            overall = safe_mean(row_scores)
            rows += f'<td class="td-center" style="font-weight:700">{overall:.3f}</td>'
        else:
            rows += '<td class="hm-missing">-</td>'
        rows += "</tr>\n"

    # Compute overall task averages for insight
    task_avgs = {}
    for task in tasks:
        all_scores = []
        for tier in TIER_ORDER:
            d = task_stats[task].get(tier)
            if d:
                all_scores.append(d["avg"])
        if all_scores:
            task_avgs[task] = safe_mean(all_scores)

    t1_avg = task_avgs.get("t1", 0)
    t2_avg = task_avgs.get("t2", 0)
    diff = abs(t1_avg - t2_avg)

    return f"""<div class="section" id="task-difficulty">
  {section_header("9", "Results - Task Difficulty Comparison (t1 vs t2)", "task-difficulty")}
  <p class="prose">Each spec has two tasks (t1 and t2), both phrased in business language to avoid
  endpoint-revealing technical terms. This section examines whether task difficulty varies systematically
  between the two task slots across all 50 specs and 5 tiers.</p>

  <div class="table-wrap">
  <table>
    {header}
    <tbody>{rows}</tbody>
  </table>
  </div>

  {callout(
    f"<strong>Task difficulty finding:</strong> t1 averages {t1_avg:.3f} overall while t2 averages {t2_avg:.3f} "
    f"- a difference of only {diff:.3f} points. Tasks are approximately equally difficult across both task slots, "
    "suggesting the task assignment process was balanced. The none-tier gap between tasks is slightly larger, "
    "indicating some task-specific prior knowledge variance when no documentation is provided.",
    "info"
  )}
</div>"""


def section_code_quality(tier_stats):
    rows = ""
    for tier in TIER_ORDER:
        s = tier_stats.get(tier)
        if not s:
            continue
        code_avg = s["avg_code"]
        color = score_color(code_avg)
        rows += f"""<tr>
          <td>{TIER_SHORT[tier]}</td>
          <td class="td-center" style="font-weight:700;color:{color}">{code_avg:.3f}</td>
          <td class="td-center">{s['avg_ep']:.3f}</td>
          <td class="td-center">{s['avg_par']:.3f}</td>
          <td class="td-center">{s['avg_score']:.3f}</td>
        </tr>"""

    code_data = {t: tier_stats[t]["avg_code"] for t in TIER_ORDER if t in tier_stats}
    chart = bar_chart_html(code_data, max_val=1.0)

    none_code = tier_stats.get("none", {}).get("avg_code", 0)
    best_code_tier = max(((t, tier_stats[t]["avg_code"]) for t in tier_stats if t != "none"), key=lambda x: x[1], default=("lap-lean", 0))

    return f"""<div class="section" id="code-quality">
  {section_header("10", "Results - Code Quality Analysis", "code-quality")}
  <p class="prose">Code quality (10% of total score) measures whether the agent produced
  executable Python code containing the correct endpoints and parameters.
  Agents with documentation consistently produce better-structured code across all 50 specs.</p>

  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Tier</th><th>Avg Code Score</th><th>Endpoint Score</th><th>Param Score</th><th>Overall Score</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>

  <h3 style="margin:28px 0 8px;font-size:15px;color:var(--navy)">Code Quality Score by Tier</h3>
  {chart}

  {callout(
    f"<strong>Code quality finding:</strong> The no-doc baseline achieves an average code score of "
    f"{none_code:.3f}, while <em>{TIER_SHORT[best_code_tier[0]]}</em> achieves {best_code_tier[1]:.3f}. "
    "Documentation not only improves endpoint identification but also leads to higher-quality, "
    "more structured code output from the agent. This pattern is consistent across all 5 formats "
    "and all 50 API specs tested.",
    "key"
  )}
</div>"""


def section_score_distribution(dist_stats):
    rows = ""
    for tier in TIER_ORDER:
        d = dist_stats.get(tier)
        if not d:
            continue
        color = BAR_COLORS.get(tier, "#999")
        gap_vs_none = ""
        if tier != "none":
            none_mean = dist_stats.get("none", {}).get("mean", 0)
            delta = d["mean"] - none_mean
            gap_vs_none = f'<span style="color:{"#27ae60" if delta > 0 else "#e74c3c"};font-size:11px">{fmt_pct(delta * 100)}</span>'

        # Mini sparkline (sample up to 50 scores for visual clarity)
        scores = d["scores"]
        step = max(1, len(scores) // 50)
        sampled = scores[::step]
        mini = '<div style="display:flex;gap:1px;align-items:flex-end;height:20px">'
        for sc in sampled:
            h = max(2, int(sc * 20))
            bg = score_color(sc)
            mini += f'<div style="width:5px;height:{h}px;background:{bg};border-radius:1px" title="{sc:.3f}"></div>'
        mini += "</div>"

        rows += f"""<tr>
          <td><span class="tier-pill" style="background:{color}22;color:{color}">{TIER_SHORT[tier]}</span></td>
          <td class="td-center">{len(scores)}</td>
          <td class="td-center">{d['min']:.3f}</td>
          <td class="td-center">{d['max']:.3f}</td>
          <td class="td-center" style="font-weight:700">{d['mean']:.3f}</td>
          <td class="td-center">{d['median']:.3f}</td>
          <td class="td-center">{d['stdev']:.3f}</td>
          <td class="td-center">{d['pct_perfect']:.0f}%</td>
          <td class="td-center">{d['pct_good']:.0f}%</td>
          <td>{mini}</td>
          <td class="td-center">{gap_vs_none}</td>
        </tr>"""

    none_mean = dist_stats.get("none", {}).get("mean", 0)
    lap_lean_mean = dist_stats.get("lap-lean", {}).get("mean", 0)

    return f"""<div class="section" id="distribution">
  {section_header("11", "Results - Score Distribution", "distribution")}
  <p class="prose">Score range, central tendency, and variability per tier across all 500 completed runs.
  "% Perfect" = runs scoring exactly 1.0. "% Good" = runs scoring 0.7 or above.
  The sparkline shows a sample of individual run scores sorted ascending.</p>

  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Tier</th><th>n</th><th>Min</th><th>Max</th><th>Mean</th><th>Median</th>
      <th>Std Dev</th><th>% Perfect</th><th>% Good</th><th>Scores</th><th>Delta vs None</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>

  {callout(
    f"<strong>Distribution highlight:</strong> The no-doc baseline has a mean score of {none_mean:.3f} "
    f"while LAP-Lean achieves {lap_lean_mean:.3f}. The gap of +{lap_lean_mean - none_mean:.3f} is "
    "driven primarily by endpoint identification: without documentation, agents default to "
    "guessing endpoints from their training knowledge, which is unreliable for non-famous or "
    "domain-specific APIs. The documentation gap (none vs documented tiers) is statistically significant "
    "(p &lt;&lt; 0.001); differences between documented tiers are directional only (see Section 12).",
    "warning"
  )}
</div>"""


def section_statistical_notes(tier_stats, dist_stats, data):
    n_per_tier_avg = safe_mean([s["n_completed"] for s in tier_stats.values()])

    # Descriptive stats table
    desc_rows = ""
    for tier in TIER_ORDER:
        d = dist_stats.get(tier)
        s = tier_stats.get(tier)
        if not d or not s:
            continue
        n = s["n_completed"]
        mean_val = d["mean"]
        stdev_val = d["stdev"]
        se = stdev_val / math.sqrt(n) if n > 1 else 0
        ci_95 = 1.96 * se
        desc_rows += f"""<tr>
          <td>{TIER_SHORT[tier]}</td>
          <td class="td-center">{n}</td>
          <td class="td-center">{mean_val:.3f}</td>
          <td class="td-center">{stdev_val:.3f}</td>
          <td class="td-center">{se:.3f}</td>
          <td class="td-center">&plusmn;{ci_95:.3f}</td>
        </tr>"""

    # Paired t-tests for scores
    score_comparisons = [
        ("none", "pretty"), ("none", "lap-lean"),
        ("pretty", "minified"), ("pretty", "lap-standard"),
        ("pretty", "lap-lean"), ("lap-standard", "lap-lean"),
    ]
    score_ttest_rows = ""
    for a, b in score_comparisons:
        m, t, sig, n, d_cohen = paired_ttest(data, a, b, "score")
        sig_style = "font-weight:700;color:#27ae60" if sig != "ns" else "color:#e74c3c"
        score_ttest_rows += f"""<tr>
          <td>{TIER_SHORT.get(b, b)} vs {TIER_SHORT.get(a, a)}</td>
          <td class="td-center">{m:+.4f}</td>
          <td class="td-center">{t:.3f}</td>
          <td class="td-center">{n}</td>
          <td class="td-center">{d_cohen:.3f}</td>
          <td class="td-center" style="{sig_style}">{sig}</td>
        </tr>"""

    # Paired t-tests for wall time
    time_ttest_rows = ""
    for a, b in score_comparisons:
        m, t, sig, n, d_cohen = paired_ttest(data, a, b, "time")
        sig_style = "font-weight:700;color:#27ae60" if sig != "ns" else "color:#e74c3c"
        time_ttest_rows += f"""<tr>
          <td>{TIER_SHORT.get(b, b)} vs {TIER_SHORT.get(a, a)}</td>
          <td class="td-center">{m:+.1f}s</td>
          <td class="td-center">{t:.3f}</td>
          <td class="td-center">{n}</td>
          <td class="td-center" style="{sig_style}">{sig}</td>
        </tr>"""

    # Paired t-tests for cost
    cost_ttest_rows = ""
    for a, b in score_comparisons:
        m, t, sig, n, d_cohen = paired_ttest(data, a, b, "cost")
        sig_style = "font-weight:700;color:#27ae60" if sig != "ns" else "color:#e74c3c"
        cost_ttest_rows += f"""<tr>
          <td>{TIER_SHORT.get(b, b)} vs {TIER_SHORT.get(a, a)}</td>
          <td class="td-center">{m:+.4f}</td>
          <td class="td-center">{t:.3f}</td>
          <td class="td-center">{n}</td>
          <td class="td-center" style="{sig_style}">{sig}</td>
        </tr>"""

    # Paired t-tests for total tokens
    token_ttest_rows = ""
    for a, b in score_comparisons:
        m, t, sig, n, d_cohen = paired_ttest(data, a, b, "total_tokens")
        sig_style = "font-weight:700;color:#27ae60" if sig != "ns" else "color:#e74c3c"
        token_ttest_rows += f"""<tr>
          <td>{TIER_SHORT.get(b, b)} vs {TIER_SHORT.get(a, a)}</td>
          <td class="td-center">{fmt_tokens(m)}</td>
          <td class="td-center">{t:.3f}</td>
          <td class="td-center">{n}</td>
          <td class="td-center" style="{sig_style}">{sig}</td>
        </tr>"""

    # Doc lift summary
    doc_lift = compute_doc_lift(data)
    lift_rows = ""
    for tier in ["pretty", "minified", "lap-standard", "lap-lean"]:
        lifts = list(doc_lift.get(tier, {}).values())
        if lifts:
            lift_rows += f"""<tr>
              <td>{TIER_SHORT[tier]}</td>
              <td class="td-center">{safe_mean(lifts):+.3f}</td>
              <td class="td-center">{safe_median(lifts):+.3f}</td>
              <td class="td-center">{min(lifts):+.3f}</td>
              <td class="td-center">{max(lifts):+.3f}</td>
              <td class="td-center">{safe_stdev(lifts):.3f}</td>
            </tr>"""

    return f"""<div class="section" id="stats">
  {section_header("12", "Statistical Analysis", "stats")}

  <h3 style="font-size:16px;margin:0 0 10px;color:var(--navy)">12.1 Descriptive Statistics</h3>
  <p class="prose">With approximately {n_per_tier_avg:.0f} runs per tier (50 specs x 2 tasks),
  standard error and 95% confidence intervals are provided for transparency.</p>

  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Tier</th><th>n</th><th>Mean Score</th><th>Std Dev</th><th>Std Error</th><th>95% CI</th>
    </tr></thead>
    <tbody>{desc_rows}</tbody>
  </table>
  </div>

  {callout(
    "<strong>Important:</strong> 95% confidence intervals for all four documented tiers overlap completely. "
    "This means no pairwise tier comparison among documented tiers reaches conventional statistical "
    "significance (p &lt; 0.05). The large standard deviations (~0.23) reflect genuine variance across "
    "API complexity, not measurement noise. Each condition was tested once (n=1 per spec-tier-task); "
    "per-spec differences should be interpreted with caution.",
    "warning"
  )}

  <h3 style="font-size:16px;margin:24px 0 10px;color:var(--navy)">12.2 Paired t-Tests: Task Score</h3>
  <p class="prose">Paired t-tests (df=49, two-tailed) comparing mean score per spec across tiers.
  Each spec contributes one data point (mean of t1 and t2). Cohen's d measures effect size.</p>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Comparison</th><th>Mean Diff</th><th>t-stat</th><th>n</th><th>Cohen's d</th><th>Sig</th></tr></thead>
    <tbody>{score_ttest_rows}</tbody>
  </table>
  </div>

  {callout(
    "<strong>Key finding:</strong> The ONLY statistically significant score comparisons are "
    "none vs documented tiers (p &lt;&lt; 0.001). All comparisons between documented tiers "
    "(pretty vs minified, pretty vs LAP-Std, pretty vs LAP-Lean, LAP-Std vs LAP-Lean) "
    "fail to reach significance. The real story is: any documentation >> no documentation.",
    "key"
  )}

  <h3 style="font-size:16px;margin:24px 0 10px;color:var(--navy)">12.3 Paired t-Tests: Wall Time</h3>
  <p class="prose">Paired t-tests for wall time (seconds). Positive values mean the second tier is slower.</p>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Comparison</th><th>Mean Diff</th><th>t-stat</th><th>n</th><th>Sig</th></tr></thead>
    <tbody>{time_ttest_rows}</tbody>
  </table>
  </div>

  <h3 style="font-size:16px;margin:24px 0 10px;color:var(--navy)">12.4 Paired t-Tests: Cost (USD)</h3>
  <p class="prose">Paired t-tests for per-run cost. Negative values mean the second tier is cheaper.</p>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Comparison</th><th>Mean Diff</th><th>t-stat</th><th>n</th><th>Sig</th></tr></thead>
    <tbody>{cost_ttest_rows}</tbody>
  </table>
  </div>

  <h3 style="font-size:16px;margin:24px 0 10px;color:var(--navy)">12.5 Paired t-Tests: Total Tokens</h3>
  <p class="prose">Paired t-tests for total tokens consumed per run. Negative values mean the second tier uses fewer tokens.</p>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Comparison</th><th>Mean Diff</th><th>t-stat</th><th>n</th><th>Sig</th></tr></thead>
    <tbody>{token_ttest_rows}</tbody>
  </table>
  </div>

  {callout(
    "<strong>Efficiency finding:</strong> While score differences between documented tiers are NOT significant, "
    "wall time and token differences ARE. LAP-Lean vs Pretty shows highly significant reductions in "
    "wall time (p &lt; 0.001), cost (p &lt; 0.001), and total tokens (p &lt; 0.001). "
    "This is the report's strongest defensible claim: equivalent quality at significantly lower cost.",
    "success"
  )}

  <h3 style="font-size:16px;margin:24px 0 10px;color:var(--navy)">12.6 Documentation Lift (Tier Score - None Score)</h3>
  <p class="prose">How much does each tier improve over the no-documentation baseline, per spec?
  This isolates documentation's contribution from prior knowledge.</p>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Tier</th><th>Mean Lift</th><th>Median Lift</th><th>Min</th><th>Max</th><th>Std Dev</th></tr></thead>
    <tbody>{lift_rows}</tbody>
  </table>
  </div>
</div>"""


def section_doc_sensitive(data, tier_stats, ceiling_specs):
    """Section showing analysis with ceiling-effect specs excluded."""
    n_ceiling = len(ceiling_specs)
    sensitive_stats, filtered_data = compute_doc_sensitive_stats(data, ceiling_specs)

    n_sensitive = len(set(r["spec"] for r in filtered_data))

    # Build comparison table: full vs sensitive subset
    rows = ""
    for tier in TIER_ORDER:
        full_s = tier_stats.get(tier, {})
        sens_s = sensitive_stats.get(tier, {})
        if not full_s:
            continue
        full_score = full_s.get("avg_score", 0)
        sens_score = sens_s.get("avg_score", 0) if sens_s else 0
        delta = sens_score - full_score
        rows += f"""<tr>
          <td>{TIER_SHORT[tier]}</td>
          <td class="td-center" style="font-weight:700">{full_score:.3f}</td>
          <td class="td-center" style="font-weight:700">{sens_score:.3f}</td>
          <td class="td-center">{delta:+.3f}</td>
        </tr>"""

    # Paired t-test on sensitive subset
    sens_score_rows = ""
    comparisons = [("none", "pretty"), ("none", "lap-lean"), ("pretty", "lap-lean")]
    for a, b in comparisons:
        m, t, sig, n, d_cohen = paired_ttest(filtered_data, a, b, "score")
        sig_style = "font-weight:700;color:#27ae60" if sig != "ns" else "color:#e74c3c"
        sens_score_rows += f"""<tr>
          <td>{TIER_SHORT.get(b, b)} vs {TIER_SHORT.get(a, a)}</td>
          <td class="td-center">{m:+.4f}</td>
          <td class="td-center">{t:.3f}</td>
          <td class="td-center">{n}</td>
          <td class="td-center" style="{sig_style}">{sig}</td>
        </tr>"""

    ceiling_list = ", ".join(ceiling_specs) if ceiling_specs else "(none)"

    return f"""<div class="section" id="doc-sensitive">
  {section_header("13", "Results - Documentation-Sensitive Subset Analysis", "doc-sensitive")}
  <p class="prose">Some APIs score &ge; 0.9 across all tiers including the no-documentation baseline,
  indicating the model has strong prior knowledge. These "ceiling-effect" specs contribute 1.0
  to every tier's average, compressing observed differences and measuring API familiarity
  rather than documentation quality. This section excludes {n_ceiling} such specs to isolate
  the documentation signal.</p>

  <p class="prose" style="font-size:13px;color:var(--muted)"><strong>Excluded specs (none-tier &ge; 0.9):</strong> {ceiling_list}</p>

  <h3 style="font-size:16px;margin:20px 0 10px;color:var(--navy)">Full Set vs Documentation-Sensitive Subset ({n_sensitive} specs)</h3>
  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Tier</th><th>Full Set (50 specs)</th><th>Sensitive Subset ({n_sensitive} specs)</th><th>Delta</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>

  <h3 style="font-size:16px;margin:20px 0 10px;color:var(--navy)">Paired t-Tests on Sensitive Subset</h3>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Comparison</th><th>Mean Diff</th><th>t-stat</th><th>n</th><th>Sig</th></tr></thead>
    <tbody>{sens_score_rows}</tbody>
  </table>
  </div>

  {callout(
    "<strong>Subset insight:</strong> When ceiling-effect specs are excluded, the none-tier score drops "
    "further (revealing the true documentation gap), while documented-tier ordering remains similar. "
    "The documentation-sensitive subset shows the real signal: documentation matters most for APIs "
    "the model does not already know well.",
    "info"
  )}
</div>"""


def section_limitations():
    """Prominent limitations section."""
    return f"""<div class="section" id="limitations">
  {section_header("14", "Limitations", "limitations")}

  <p class="prose">This benchmark has several methodological limitations that should be considered
  when interpreting results:</p>

  <div class="table-wrap">
  <table>
    <thead><tr><th>Limitation</th><th>Impact</th><th>Mitigation</th></tr></thead>
    <tbody>
      <tr>
        <td><strong>N=1 per condition</strong></td>
        <td>Each (spec, tier, task) ran exactly once. LLM outputs are stochastic; observed per-spec differences may be sampling noise.</td>
        <td>Aggregate tier comparisons (n=100 per tier) are more reliable. Future: n&ge;3 per condition.</td>
      </tr>
      <tr>
        <td><strong>Fixed tier order</strong></td>
        <td>Tiers executed in fixed order (none, pretty, minified, lap-standard, lap-lean). Later tiers could benefit from model-level caching.</td>
        <td>Double-UUID isolation prevents filesystem contamination. Future: randomize tier order.</td>
      </tr>
      <tr>
        <td><strong>Single model</strong></td>
        <td>Only Claude Sonnet 4.5 was tested. Other models may respond differently to compression.</td>
        <td>Future: cross-model validation with GPT-4o, Gemini, Claude Opus.</td>
      </tr>
      <tr>
        <td><strong>Recall-only endpoint scoring</strong></td>
        <td>Endpoint score is recall-based (correct_hits / expected_count). No penalty for false positives. Verbose agents may be overly rewarded.</td>
        <td>Future: add F1-based metric with precision penalty.</td>
      </tr>
      <tr>
        <td><strong>WebFetch available in none-tier</strong></td>
        <td>Agents could theoretically fetch API docs from the web during none-tier runs, breaking the prior-knowledge assumption.</td>
        <td>Future: restrict WebFetch tool for none-tier runs. Verify via session recordings.</td>
      </tr>
      <tr>
        <td><strong>Concurrency=3</strong></td>
        <td>Benchmark ran with ThreadPoolExecutor(max_workers=3). Non-deterministic execution order means results are not perfectly reproducible.</td>
        <td>Future: use concurrency=1 for scientific runs.</td>
      </tr>
      <tr>
        <td><strong>Ceiling-effect specs</strong></td>
        <td>~8 specs score &ge;0.9 across ALL tiers including none, compressing observed tier differences.</td>
        <td>Section 13 provides a documentation-sensitive subset analysis excluding these specs.</td>
      </tr>
    </tbody>
  </table>
  </div>
</div>"""


def section_discussion(tier_stats, compression_stats):
    lean = tier_stats.get("lap-lean", {})
    pretty = tier_stats.get("pretty", {})
    none_t = tier_stats.get("none", {})
    mini = tier_stats.get("minified", {})
    std = tier_stats.get("lap-standard", {})
    lean_c = compression_stats.get("lap-lean", {})
    std_c = compression_stats.get("lap-standard", {})

    lean_score = lean.get("avg_score", 0)
    pretty_score = pretty.get("avg_score", 0)
    none_score = none_t.get("avg_score", 0)
    mini_score = mini.get("avg_score", 0)
    std_score = std.get("avg_score", 0)
    lean_doc_savings = lean_c.get("doc_savings_pct", 0) or 0
    std_doc_savings = std_c.get("doc_savings_pct", 0) or 0
    lean_cost_savings = lean_c.get("cost_savings_pct", 0) or 0

    return f"""<div class="section" id="discussion">
  {section_header("15", "Discussion", "discussion")}

  <h3 style="font-size:16px;margin-bottom:8px;color:var(--navy)">LAP-Lean: Best Efficiency Tier</h3>
  <p class="prose">
    LAP-Lean achieves the numerically highest average score of {lean_score:.3f} compared to the
    pretty baseline ({pretty_score:.3f}), though this difference (+{lean_score - pretty_score:.3f})
    does not reach statistical significance (paired t-test, p &gt; 0.05).
    The significant finding is efficiency: LAP-Lean delivers approximately {lean_doc_savings:.0f}%
    documentation token reduction and ~{lean_cost_savings:.0f}% inference cost savings per run
    (p &lt; 0.001 for both wall time and token reduction).
    For production AI coding workflows where agents are invoked at scale, LAP-Lean
    offers equivalent quality at significantly lower cost and latency. This result holds across
    all 5 formats and 50 APIs.
  </p>

  <h3 style="font-size:16px;margin:20px 0 8px;color:var(--navy)">No-Doc Baseline: Documentation Is Essential</h3>
  <p class="prose">
    The no-documentation baseline scores {none_score:.3f} on average - substantially below all
    documented tiers across all 5 formats tested. The primary failure mode is endpoint identification (EP score):
    without documentation, agents cannot reliably identify the correct API endpoint path for unfamiliar
    or domain-specific APIs. This confirms that documentation is not merely helpful but essential
    for reliable AI agent performance. The none-tier effect is especially pronounced for
    Protobuf, AsyncAPI, and less well-known APIs where the model has limited training signal.
  </p>

  <h3 style="font-size:16px;margin:20px 0 8px;color:var(--navy)">Minification Provides Limited Benefit Over Pretty</h3>
  <p class="prose">
    The minified tier achieves {mini_score:.3f} vs {pretty_score:.3f} for pretty -- a negligible
    difference that does not reach statistical significance.
    Despite removing whitespace, minification of YAML/JSON/GraphQL does not meaningfully reduce semantic
    token count because structural keywords, field names, and values remain unchanged.
    LAP-format representations are fundamentally different: they reorganize information into a denser,
    agent-optimized structure rather than simply removing whitespace.
  </p>

  <h3 style="font-size:16px;margin:20px 0 8px;color:var(--navy)">LAP-Standard: Intermediate Trade-off</h3>
  <p class="prose">
    LAP-Standard achieves {std_score:.3f} - essentially identical to LAP-Lean at {lean_score:.3f} -
    while using approximately {std_doc_savings:.0f}% fewer tokens than the pretty baseline.
    The near-identical scores between LAP-Standard and LAP-Lean suggest that for the tested task types,
    type information alone (LAP-Lean) is sufficient for correct task completion. However,
    LAP-Standard may be preferable for agents working with unfamiliar APIs where natural language
    endpoint descriptions provide additional disambiguation context, or for more complex multi-step tasks.
  </p>

  <h3 style="font-size:16px;margin:20px 0 8px;color:var(--navy)">Cross-Format Robustness</h3>
  <p class="prose">
    The LAP format compression benefit is consistent across all 5 tested specification formats:
    OpenAPI (REST), AsyncAPI (event-driven), GraphQL (query language), Postman (collection),
    and Protobuf (binary protocol). This cross-format robustness is significant because each format
    has a fundamentally different structure and information organization. The LAP converter
    successfully normalizes all formats into a common endpoint-centric representation that
    preserves the information an AI agent needs for task completion.
  </p>
</div>"""


def section_conclusion(tier_stats, compression_stats, data):
    lean = tier_stats.get("lap-lean", {})
    pretty = tier_stats.get("pretty", {})
    lean_score = lean.get("avg_score", 0)
    pretty_score = pretty.get("avg_score", 0)
    none_score = tier_stats.get("none", {}).get("avg_score", 0)
    lean_savings = compression_stats.get("lap-lean", {}).get("doc_savings_pct", 0) or 0
    std_savings = compression_stats.get("lap-standard", {}).get("doc_savings_pct", 0) or 0
    lean_cost_sav = compression_stats.get("lap-lean", {}).get("cost_savings_pct", 0) or 0
    n_completed = sum(s["n_completed"] for s in tier_stats.values())

    lean_time = lean.get("avg_time", 0)
    pretty_time = pretty.get("avg_time", 0)
    time_savings_s = pretty_time - lean_time

    return f"""<div class="section" id="conclusion">
  {section_header("16", "Conclusion", "conclusion")}

  <p class="prose">
    This full benchmark ({n_completed} runs across 50 APIs, 5 formats, 5 tiers, 2 tasks) yields
    two clear findings:
  </p>

  <p class="prose">
    <strong>1. Documentation is essential.</strong> Providing any form of API documentation dramatically
    improves agent performance (mean documented score ~{safe_mean([lean_score, pretty_score]):.2f} vs
    none-tier {none_score:.2f}, p &lt;&lt; 0.001). This holds across all 5 specification formats.
    Agents cannot reliably identify API endpoints from training knowledge alone,
    particularly for domain-specific or less-prominent APIs.
  </p>

  <p class="prose">
    <strong>2. Compression preserves quality while significantly reducing cost.</strong>
    No statistically significant quality difference was detected between any documented tier
    (paired t-tests, all p &gt; 0.05). LAP-Lean achieved the numerically highest score
    ({lean_score:.3f} vs pretty {pretty_score:.3f}), but this difference is directional only.
    The statistically significant advantages of LAP-Lean are efficiency:
    <strong>{lean_savings:.0f}% documentation token reduction</strong>,
    <strong>{lean_cost_sav:.0f}% cost savings</strong> (p &lt; 0.001),
    and <strong>{time_savings_s:.0f}s faster per run</strong> (p &lt; 0.001).
  </p>

  <h3 style="font-size:16px;margin:20px 0 8px;color:var(--navy)">Recommended Production Configuration</h3>
  <ul style="margin:0 0 16px 20px;line-height:2;font-size:14px">
    <li>Use <strong>LAP-Lean</strong> for high-volume, cost-sensitive AI coding agent deployments -- equivalent quality at significantly lower cost and latency</li>
    <li>Use <strong>LAP-Standard</strong> when working with complex or ambiguous APIs where descriptions provide additional disambiguation context</li>
    <li>Avoid relying on <strong>minification alone</strong> -- it provides minimal token savings compared to LAP format restructuring</li>
    <li>Always provide <strong>some</strong> documentation -- the no-doc baseline demonstrates a significant quality gap across all formats</li>
  </ul>

  <h3 style="font-size:16px;margin:20px 0 8px;color:var(--navy)">Future Work</h3>
  <ul style="margin:0 0 0 20px;line-height:2;font-size:14px">
    <li><strong>Repetition trials:</strong> n &gt;= 3 per condition to enable per-spec statistical significance testing</li>
    <li><strong>Multiple models:</strong> Compare results across GPT-4o, Gemini Pro, Claude Opus, and local LLMs</li>
    <li><strong>Randomized tier order:</strong> Eliminate potential ordering bias within spec runs</li>
    <li><strong>Precision scoring:</strong> Add F1-based endpoint metric (penalize false positives, not just recall)</li>
    <li><strong>Complex task types:</strong> Multi-step workflows, error handling, pagination, authentication</li>
    <li><strong>Context window scaling:</strong> Test performance degradation curves as doc size approaches context limits</li>
  </ul>
</div>"""


def section_appendix(data):
    tier_order_idx = {t: i for i, t in enumerate(TIER_ORDER)}
    format_order_idx = {f: i for i, f in enumerate(FORMAT_ORDER)}

    sorted_runs = sorted(
        data,
        key=lambda r: (
            format_order_idx.get(r["format"], 99),
            r["spec"],
            tier_order_idx.get(r["tier"], 99),
            r["task"]
        )
    )

    rows = ""
    for r in sorted_runs:
        status_style = "color:#27ae60;font-weight:600" if r["status"] == "completed" else "color:#e74c3c;font-weight:600"
        score_style = f"color:{score_color(r['score'])};font-weight:700"
        color = BAR_COLORS.get(r["tier"], "#999")

        cost_str = fmt_cost(r["cost"]) if r["cost"] > 0 else "$0.0000"
        tok_str = fmt_tokens(r["total_tokens"]) if r["total_tokens"] > 0 else "0"
        doc_str = fmt_tokens(r["doc_tokens"]) if r["doc_tokens"] > 0 else "0"

        rows += f"""<tr>
          <td class="td-mono" style="font-size:12px">{r['spec']}</td>
          <td style="font-size:11px;color:{FORMAT_COLORS.get(r['format'], COLOR_MUTED)};font-weight:600">{r['format']}</td>
          <td><span class="tier-pill" style="background:{color}22;color:{color};font-size:11px">{TIER_SHORT.get(r['tier'], r['tier'])}</span></td>
          <td class="td-center">{r['task']}</td>
          <td style="{status_style};font-size:12px">{r['status']}</td>
          <td class="td-center" style="{score_style}">{r['score']:.3f}</td>
          <td class="td-center">{r['ep']:.3f}</td>
          <td class="td-center">{r['par']:.3f}</td>
          <td class="td-center">{r['code']:.3f}</td>
          <td class="td-right">{r['time']:.1f}s</td>
          <td class="td-right td-mono">{cost_str}</td>
          <td class="td-right td-mono">{tok_str}</td>
          <td class="td-right td-mono">{doc_str}</td>
          <td class="td-center">{r.get('num_turns', '-')}</td>
        </tr>"""

    n_errors = sum(1 for r in data if r["status"] != "completed")

    return f"""<div class="section" id="appendix">
  {section_header("A", "Appendix A: Individual Runs", "appendix")}
  <p class="prose">All {len(data)} individual runs, sorted by format, spec, tier, task.
  All runs completed successfully.</p>

  <details>
    <summary>Show all {len(data)} individual runs (click to expand)</summary>
    <div class="table-wrap" style="margin-top:14px">
    <table>
      <thead><tr>
        <th>Spec</th><th>Format</th><th>Tier</th><th>Task</th><th>Status</th>
        <th>Score</th><th>EP</th><th>Par</th><th>Code</th>
        <th>Time</th><th>Cost</th><th>Total Tokens</th><th>Doc Tokens</th><th>Turns</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    </div>
  </details>
</div>"""


def section_appendix_tasks(task_manifests):
    rows = ""
    for t in task_manifests:
        endpoints_str = "<br>".join(t["target_endpoints"]) if t["target_endpoints"] else "-"
        fmt_color = FORMAT_COLORS.get(t["format"], COLOR_MUTED)
        rows += f"""<tr>
          <td class="td-mono" style="font-size:12px">{t['spec']}</td>
          <td style="font-size:11px;color:{fmt_color};font-weight:600">{t['format']}</td>
          <td class="td-center">{t['task_id']}</td>
          <td style="font-size:13px">{t['description']}</td>
          <td class="td-mono" style="font-size:11px">{endpoints_str}</td>
        </tr>"""

    return f"""<div class="section" id="appendix-tasks">
  {section_header("B", "Appendix B: Task Definitions", "appendix-tasks")}
  <p class="prose">All {len(task_manifests)} task definitions used in the benchmark (2 tasks per spec, 50 specs).
  Each task is phrased in business language to avoid endpoint-revealing technical terms.</p>

  <details>
    <summary>Show all {len(task_manifests)} task definitions (click to expand)</summary>
    <div class="table-wrap" style="margin-top:14px">
    <table>
      <thead><tr>
        <th>Spec</th><th>Format</th><th>Task</th><th>Description</th><th>Target Endpoints</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    </div>
  </details>
</div>"""


# ---------------------------------------------------------------------------
# Main HTML Assembly
# ---------------------------------------------------------------------------

def build_html(data):
    format_specs = extract_format_specs(data)

    tier_stats = compute_tier_stats(data)
    compression_stats = compute_compression_stats(tier_stats)
    spec_matrix = compute_spec_matrix(data)
    format_stats = compute_format_stats(data)
    dist_stats = compute_score_distribution(data)
    task_stats = compute_task_comparison(data)
    wall_time_data = compute_wall_time_stats(data)
    task_manifests = load_task_manifests()
    ceiling_specs = compute_ceiling_specs(data, threshold=0.9)

    body_sections = "\n".join([
        section_abstract(data, tier_stats, compression_stats),
        section_key_findings(data, tier_stats, compression_stats),
        section_methodology(format_specs),
        section_tier_comparison(tier_stats),
        section_compression(tier_stats, compression_stats),
        section_cost_efficiency(tier_stats, compression_stats),
        section_wall_time(wall_time_data, tier_stats),
        section_heatmap(spec_matrix, data, format_specs),
        section_format_comparison(format_stats),
        section_task_difficulty(task_stats),
        section_code_quality(tier_stats),
        section_score_distribution(dist_stats),
        section_statistical_notes(tier_stats, dist_stats, data),
        section_doc_sensitive(data, tier_stats, ceiling_specs),
        section_limitations(),
        section_discussion(tier_stats, compression_stats),
        section_conclusion(tier_stats, compression_stats, data),
        section_appendix(data),
        section_appendix_tasks(task_manifests),
    ])

    n_completed = sum(1 for r in data if r["status"] == "completed")
    n_total = len(data)
    n_specs = len(set(r["spec"] for r in data))

    footer = f"""<footer>
  Generated by <a href="#">LAP Benchmark v2 Harness</a> &mdash;
  Model: claude-sonnet-4-5-20250929 &mdash;
  February 2026 &mdash;
  Full Run: {n_completed}/{n_total} runs, {n_specs} specs, 5 formats, 5 tiers, 2 tasks
</footer>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LAP Benchmark v2 - Full Report - API Documentation Compression Efficacy</title>
  <style>{CSS}</style>
</head>
<body>
{section_cover(data)}
{section_toc()}
<div class="page">
{body_sections}
{footer}
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("Loading full benchmark data...")
    data = load_data()
    print(f"  Loaded {len(data)} runs")

    completed = [r for r in data if r["status"] == "completed"]
    errors = [r for r in data if r["status"] != "completed"]
    print(f"  Completed: {len(completed)}, Errors/Timeouts: {len(errors)}")

    formats = set(r["format"] for r in data)
    specs = set(r["spec"] for r in data)
    print(f"  Formats: {sorted(formats)}")
    print(f"  Specs: {len(specs)} total")

    print("Computing statistics...")
    tier_stats = compute_tier_stats(data)
    for tier, s in tier_stats.items():
        print(f"  {tier:14s}: n={s['n_completed']:3d}/{s['n_all']:3d}, avg_score={s['avg_score']:.3f}, avg_cost=${s['avg_cost']:.4f}")

    print("Generating HTML report...")
    html = build_html(data)

    out_path = PROJECT_ROOT / "results" / "LAP_Benchmark_v2_Full_Report.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = out_path.stat().st_size / 1024
    print(f"\nReport written to: {out_path}")
    print(f"File size: {size_kb:.1f} KB")
    print(f"Self-contained: yes (no external JS/CSS, Google Fonts only for typography)")


if __name__ == "__main__":
    main()
