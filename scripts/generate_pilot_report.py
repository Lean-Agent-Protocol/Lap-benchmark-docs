#!/usr/bin/env python3
"""Generate HTML report from pilot benchmark data.

This script reads results/pilot_data.json and generates a self-contained
HTML report with visualizations and analysis.

Usage:
    python scripts/generate_pilot_report.py
"""

import json
from pathlib import Path
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_pilot_data():
    """Load pilot data JSON."""
    pilot_path = PROJECT_ROOT / "results" / "pilot_data.json"
    with open(pilot_path, encoding="utf-8") as f:
        return json.load(f)


def calculate_tier_stats(data):
    """Calculate statistics per tier (excluding failed/timeout runs)."""
    tier_data = defaultdict(list)

    for run in data:
        if run["status"] == "completed":
            tier_data[run["tier"]].append(run)

    stats = {}
    tier_order = ["none", "pretty", "minified", "lap-standard", "lap-lean"]

    for tier in tier_order:
        runs = tier_data.get(tier, [])
        if not runs:
            continue

        stats[tier] = {
            "count": len(runs),
            "avg_score": sum(r["score"] for r in runs) / len(runs),
            "avg_endpoint": sum(r["ep"] for r in runs) / len(runs),
            "avg_params": sum(r["par"] for r in runs) / len(runs),
            "avg_code": sum(r["code"] for r in runs) / len(runs),
            "avg_time": sum(r["time"] for r in runs) / len(runs),
            "avg_cost": sum(r["cost"] for r in runs) / len(runs),
            "avg_tokens": sum(r["total_tokens"] for r in runs) / len(runs),
        }

    return stats


def calculate_spec_tier_matrix(data):
    """Calculate score matrix: rows = specs, cols = tiers."""
    matrix = defaultdict(dict)

    for run in data:
        if run["status"] == "completed":
            spec = run["spec"]
            tier = run["tier"]
            matrix[spec][tier] = run["score"]

    return dict(matrix)


def calculate_code_quality_breakdown(data):
    """Calculate code quality sub-scores per tier.

    Note: This requires access to code_detail in score object,
    which may not be in pilot_data.json. We'll extract from run files.
    """
    from pathlib import Path
    import json

    # Try to load from the latest batch
    runs_dir = PROJECT_ROOT / "results" / "runs"
    batches = sorted([d for d in runs_dir.iterdir() if d.is_dir()], reverse=True)

    if not batches:
        return {}

    tier_code_stats = defaultdict(lambda: {
        "has_code_count": 0,
        "endpoints_in_code_sum": 0.0,
        "params_in_code_sum": 0.0,
        "no_hallucination_count": 0,
        "total_runs": 0,
    })

    # Load from most recent batch
    latest_batch = batches[0]
    run_files = [f for f in latest_batch.glob("*.json") if f.name != "manifest.json"]

    for run_file in run_files:
        with open(run_file, encoding="utf-8") as f:
            run = json.load(f)

        if run["execution"]["status"] != "completed":
            continue

        tier = run["tier"]
        code_detail = run.get("score", {}).get("code_detail", {})

        tier_code_stats[tier]["total_runs"] += 1
        if code_detail.get("has_code"):
            tier_code_stats[tier]["has_code_count"] += 1
        tier_code_stats[tier]["endpoints_in_code_sum"] += code_detail.get("endpoints_in_code", 0.0)
        tier_code_stats[tier]["params_in_code_sum"] += code_detail.get("params_in_code", 0.0)
        if code_detail.get("no_hallucination"):
            tier_code_stats[tier]["no_hallucination_count"] += 1

    # Convert to averages
    result = {}
    for tier, stats in tier_code_stats.items():
        total = stats["total_runs"]
        if total == 0:
            continue
        result[tier] = {
            "has_code": stats["has_code_count"] / total,
            "endpoints_in_code": stats["endpoints_in_code_sum"] / total,
            "params_in_code": stats["params_in_code_sum"] / total,
            "no_hallucination": stats["no_hallucination_count"] / total,
        }

    return result


def score_to_color(score):
    """Map score to color: green >= 0.9, yellow >= 0.7, orange >= 0.5, red < 0.5."""
    if score >= 0.9:
        return "#22c55e"  # green
    elif score >= 0.7:
        return "#eab308"  # yellow
    elif score >= 0.5:
        return "#f97316"  # orange
    else:
        return "#ef4444"  # red


def generate_html_report(data):
    """Generate self-contained HTML report."""
    tier_stats = calculate_tier_stats(data)
    spec_matrix = calculate_spec_tier_matrix(data)
    code_quality = calculate_code_quality_breakdown(data)

    # Calculate executive summary
    completed_runs = [r for r in data if r["status"] == "completed"]
    total_runs = len(data)
    avg_score = sum(r["score"] for r in completed_runs) / len(completed_runs) if completed_runs else 0
    avg_cost = sum(r["cost"] for r in completed_runs) / len(completed_runs) if completed_runs else 0
    avg_time = sum(r["time"] for r in completed_runs) / len(completed_runs) if completed_runs else 0

    # Find best tier (highest avg score)
    best_tier = max(tier_stats.items(), key=lambda x: x[1]["avg_score"]) if tier_stats else ("N/A", {"avg_score": 0})

    # Start HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LAP Benchmark v2 - Pilot Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            background: #f9fafb;
        }}

        .header {{
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            color: white;
            padding: 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .header h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}

        .header .subtitle {{
            opacity: 0.9;
            font-size: 1rem;
        }}

        .notice {{
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 1rem;
            margin: 2rem;
            border-radius: 4px;
        }}

        .notice strong {{
            color: #92400e;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}

        .section {{
            background: white;
            border-radius: 8px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .section h2 {{
            color: #1e3a8a;
            margin-bottom: 1.5rem;
            font-size: 1.5rem;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 0.5rem;
        }}

        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .card {{
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            padding: 1.5rem;
            border-radius: 8px;
            border: 1px solid #bae6fd;
        }}

        .card .label {{
            color: #0369a1;
            font-size: 0.875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .card .value {{
            color: #1e3a8a;
            font-size: 2rem;
            font-weight: 700;
            margin-top: 0.5rem;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}

        th {{
            background: #f1f5f9;
            color: #1e3a8a;
            font-weight: 600;
            text-align: left;
            padding: 0.75rem;
            border-bottom: 2px solid #cbd5e1;
        }}

        td {{
            padding: 0.75rem;
            border-bottom: 1px solid #e2e8f0;
        }}

        tr:hover {{
            background: #f8fafc;
        }}

        .best {{
            color: #16a34a;
            font-weight: 600;
        }}

        .chart {{
            margin: 2rem 0;
        }}

        .bar {{
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
        }}

        .bar-label {{
            width: 120px;
            font-weight: 500;
            color: #475569;
        }}

        .bar-fill {{
            height: 32px;
            background: linear-gradient(90deg, #3b82f6 0%, #60a5fa 100%);
            border-radius: 4px;
            display: flex;
            align-items: center;
            padding: 0 0.75rem;
            color: white;
            font-weight: 600;
            font-size: 0.875rem;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }}

        .score-cell {{
            text-align: center;
            font-weight: 600;
            border-radius: 4px;
            color: white;
            padding: 0.5rem;
        }}

        details {{
            margin-top: 1rem;
        }}

        summary {{
            cursor: pointer;
            padding: 0.75rem;
            background: #f1f5f9;
            border-radius: 4px;
            font-weight: 600;
            color: #1e3a8a;
        }}

        summary:hover {{
            background: #e2e8f0;
        }}

        .run-detail {{
            font-size: 0.875rem;
            margin-top: 0.5rem;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>LAP Benchmark v2 - Pilot Report</h1>
        <div class="subtitle">Automated scoring of documentation compression effectiveness</div>
    </div>

    <div class="notice">
        <strong>Note:</strong> This report was generated after applying scorer fixes (path segment matching + SDK detection).
        Scores have been recomputed using the updated scoring logic.
    </div>

    <div class="container">
        <!-- Executive Summary -->
        <div class="section">
            <h2>Executive Summary</h2>
            <div class="cards">
                <div class="card">
                    <div class="label">Total Runs</div>
                    <div class="value">{total_runs}</div>
                </div>
                <div class="card">
                    <div class="label">Avg Score</div>
                    <div class="value">{avg_score:.3f}</div>
                </div>
                <div class="card">
                    <div class="label">Avg Cost</div>
                    <div class="value">${avg_cost:.3f}</div>
                </div>
                <div class="card">
                    <div class="label">Avg Time</div>
                    <div class="value">{avg_time:.1f}s</div>
                </div>
            </div>
        </div>

        <!-- Tier Comparison Table -->
        <div class="section">
            <h2>Tier Comparison</h2>
            <table>
                <thead>
                    <tr>
                        <th>Tier</th>
                        <th>Runs</th>
                        <th>Avg Score</th>
                        <th>Avg Endpoint</th>
                        <th>Avg Params</th>
                        <th>Avg Code</th>
                        <th>Avg Time (s)</th>
                        <th>Avg Cost ($)</th>
                    </tr>
                </thead>
                <tbody>
"""

    tier_order = ["none", "pretty", "minified", "lap-standard", "lap-lean"]
    for tier in tier_order:
        if tier not in tier_stats:
            continue
        stats = tier_stats[tier]
        is_best = tier == best_tier[0]
        best_class = ' class="best"' if is_best else ''
        html += f"""                    <tr>
                        <td><strong>{tier}</strong></td>
                        <td>{stats['count']}</td>
                        <td{best_class}>{stats['avg_score']:.3f}</td>
                        <td>{stats['avg_endpoint']:.3f}</td>
                        <td>{stats['avg_params']:.3f}</td>
                        <td>{stats['avg_code']:.3f}</td>
                        <td>{stats['avg_time']:.1f}</td>
                        <td>${stats['avg_cost']:.3f}</td>
                    </tr>
"""

    html += """                </tbody>
            </table>
        </div>

        <!-- Tier Comparison Chart -->
        <div class="section">
            <h2>Tier Comparison Chart</h2>
            <div class="chart">
"""

    # Find max score for scaling bars
    max_score = max([stats["avg_score"] for stats in tier_stats.values()]) if tier_stats else 1.0

    for tier in tier_order:
        if tier not in tier_stats:
            continue
        stats = tier_stats[tier]
        width_pct = (stats["avg_score"] / max_score) * 100 if max_score > 0 else 0
        html += f"""                <div class="bar">
                    <div class="bar-label">{tier}</div>
                    <div class="bar-fill" style="width: {width_pct}%;">{stats['avg_score']:.3f}</div>
                </div>
"""

    html += """            </div>
        </div>

        <!-- Score Breakdown by Spec -->
        <div class="section">
            <h2>Score Breakdown by Spec</h2>
            <table>
                <thead>
                    <tr>
                        <th>Spec</th>
"""

    for tier in tier_order:
        html += f"                        <th>{tier}</th>\n"

    html += """                    </tr>
                </thead>
                <tbody>
"""

    for spec in sorted(spec_matrix.keys()):
        html += f"                    <tr>\n                        <td><strong>{spec}</strong></td>\n"
        for tier in tier_order:
            score = spec_matrix[spec].get(tier)
            if score is not None:
                color = score_to_color(score)
                html += f'                        <td class="score-cell" style="background:{color}">{score:.3f}</td>\n'
            else:
                html += '                        <td>-</td>\n'
        html += "                    </tr>\n"

    html += """                </tbody>
            </table>
        </div>

        <!-- Code Quality Deep Dive -->
        <div class="section">
            <h2>Code Quality Deep Dive</h2>
            <p style="margin-bottom: 1rem; color: #64748b;">
                Breakdown of code quality sub-scores per tier. This shows how well agents
                incorporate endpoints and parameters into executable code blocks.
            </p>
            <table>
                <thead>
                    <tr>
                        <th>Tier</th>
                        <th>Has Code</th>
                        <th>Endpoints in Code</th>
                        <th>Params in Code</th>
                        <th>No Hallucination</th>
                    </tr>
                </thead>
                <tbody>
"""

    for tier in tier_order:
        if tier not in code_quality:
            continue
        cq = code_quality[tier]
        html += f"""                    <tr>
                        <td><strong>{tier}</strong></td>
                        <td>{cq['has_code']:.1%}</td>
                        <td>{cq['endpoints_in_code']:.3f}</td>
                        <td>{cq['params_in_code']:.3f}</td>
                        <td>{cq['no_hallucination']:.1%}</td>
                    </tr>
"""

    html += """                </tbody>
            </table>
        </div>

        <!-- Efficiency Analysis -->
        <div class="section">
            <h2>Efficiency Analysis</h2>
            <p style="margin-bottom: 1rem; color: #64748b;">
                Token usage, cost, and time comparisons. Savings are calculated relative to the "pretty" tier.
            </p>
            <table>
                <thead>
                    <tr>
                        <th>Tier</th>
                        <th>Avg Tokens</th>
                        <th>Token Savings</th>
                        <th>Avg Cost</th>
                        <th>Cost Savings</th>
                        <th>Avg Time (s)</th>
                        <th>Time Savings</th>
                    </tr>
                </thead>
                <tbody>
"""

    # Calculate savings relative to pretty tier
    pretty_tokens = tier_stats.get("pretty", {}).get("avg_tokens", 0)
    pretty_cost = tier_stats.get("pretty", {}).get("avg_cost", 0)
    pretty_time = tier_stats.get("pretty", {}).get("avg_time", 0)

    for tier in tier_order:
        if tier not in tier_stats:
            continue
        stats = tier_stats[tier]

        token_savings = ((pretty_tokens - stats["avg_tokens"]) / pretty_tokens * 100) if pretty_tokens > 0 else 0
        cost_savings = ((pretty_cost - stats["avg_cost"]) / pretty_cost * 100) if pretty_cost > 0 else 0
        time_savings = ((pretty_time - stats["avg_time"]) / pretty_time * 100) if pretty_time > 0 else 0

        html += f"""                    <tr>
                        <td><strong>{tier}</strong></td>
                        <td>{stats['avg_tokens']:.0f}</td>
                        <td>{token_savings:+.1f}%</td>
                        <td>${stats['avg_cost']:.3f}</td>
                        <td>{cost_savings:+.1f}%</td>
                        <td>{stats['avg_time']:.1f}</td>
                        <td>{time_savings:+.1f}%</td>
                    </tr>
"""

    html += """                </tbody>
            </table>
        </div>

        <!-- Individual Runs -->
        <div class="section">
            <h2>Individual Runs</h2>
            <details>
                <summary>Show all {0} runs (click to expand)</summary>
                <table>
                    <thead>
                        <tr>
                            <th>Spec</th>
                            <th>Tier</th>
                            <th>Task</th>
                            <th>Status</th>
                            <th>Score</th>
                            <th>EP</th>
                            <th>Par</th>
                            <th>Code</th>
                            <th>Time (s)</th>
                            <th>Cost ($)</th>
                        </tr>
                    </thead>
                    <tbody>
""".format(len(data))

    # Sort runs by spec, tier, task
    sorted_runs = sorted(data, key=lambda r: (r["spec"], tier_order.index(r["tier"]) if r["tier"] in tier_order else 99, r["task"]))

    for run in sorted_runs:
        status_color = "#22c55e" if run["status"] == "completed" else "#ef4444"
        html += f"""                        <tr>
                            <td>{run['spec']}</td>
                            <td>{run['tier']}</td>
                            <td>{run['task']}</td>
                            <td style="color:{status_color};font-weight:600">{run['status']}</td>
                            <td>{run['score']:.3f}</td>
                            <td>{run['ep']:.3f}</td>
                            <td>{run['par']:.3f}</td>
                            <td>{run['code']:.3f}</td>
                            <td>{run['time']:.1f}</td>
                            <td>${run['cost']:.4f}</td>
                        </tr>
"""

    html += """                    </tbody>
                </table>
            </details>
        </div>
    </div>
</body>
</html>
"""

    return html


def main():
    """Generate the HTML report."""
    print("Loading pilot data...")
    data = load_pilot_data()

    print("Generating HTML report...")
    html = generate_html_report(data)

    output_path = PROJECT_ROOT / "results" / "pilot_report.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nReport generated: {output_path}")
    print(f"Total runs processed: {len(data)}")


if __name__ == "__main__":
    main()
