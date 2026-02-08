#!/usr/bin/env python3
"""Generate benchmark comparison charts."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

with open('/data/workspace/lap-benchmark-docs/results/batch_20260208_181843/pilot_stats.json') as f:
    stats = json.load(f)

specs = ['petstore', 'proto-storage', 'snyk']
labels = ['Petstore\n(22KB)', 'Proto Storage\n(140KB)', 'Snyk\n(1MB)']

verbose_tokens = [stats[f'{s}-verbose']['total'] for s in specs]
doclean_tokens = [stats[f'{s}-doclean']['total'] for s in specs]
verbose_cost = [stats[f'{s}-verbose']['cost'] for s in specs]
doclean_cost = [stats[f'{s}-doclean']['cost'] for s in specs]
verbose_time = [stats[f'{s}-verbose']['duration_s'] for s in specs]
doclean_time = [stats[f'{s}-doclean']['duration_s'] for s in specs]
verbose_tools = [stats[f'{s}-verbose']['tools'] for s in specs]
doclean_tools = [stats[f'{s}-doclean']['tools'] for s in specs]

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('DocLean vs Verbose — Pilot Benchmark Results', fontsize=16, fontweight='bold')

x = np.arange(len(specs))
width = 0.35

colors_v = '#e74c3c'
colors_d = '#2ecc71'

# Token count
ax = axes[0, 0]
bars1 = ax.bar(x - width/2, verbose_tokens, width, label='Verbose', color=colors_v, alpha=0.85)
bars2 = ax.bar(x + width/2, doclean_tokens, width, label='DocLean', color=colors_d, alpha=0.85)
ax.set_ylabel('Total Tokens')
ax.set_title('Total Token Usage')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()
ax.set_yscale('log')
for bar, val in zip(bars1, verbose_tokens):
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{val:,}', ha='center', va='bottom', fontsize=8)
for bar, val in zip(bars2, doclean_tokens):
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{val:,}', ha='center', va='bottom', fontsize=8)

# Cost
ax = axes[0, 1]
bars1 = ax.bar(x - width/2, verbose_cost, width, label='Verbose', color=colors_v, alpha=0.85)
bars2 = ax.bar(x + width/2, doclean_cost, width, label='DocLean', color=colors_d, alpha=0.85)
ax.set_ylabel('Cost ($)')
ax.set_title('Cost per Task')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()
for bar, val in zip(bars1, verbose_cost):
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'${val:.3f}', ha='center', va='bottom', fontsize=8)
for bar, val in zip(bars2, doclean_cost):
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'${val:.3f}', ha='center', va='bottom', fontsize=8)

# Time
ax = axes[1, 0]
bars1 = ax.bar(x - width/2, verbose_time, width, label='Verbose', color=colors_v, alpha=0.85)
bars2 = ax.bar(x + width/2, doclean_time, width, label='DocLean', color=colors_d, alpha=0.85)
ax.set_ylabel('Wall Time (seconds)')
ax.set_title('Execution Time')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()
for bar, val in zip(bars1, verbose_time):
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{val:.0f}s', ha='center', va='bottom', fontsize=8)
for bar, val in zip(bars2, doclean_time):
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{val:.0f}s', ha='center', va='bottom', fontsize=8)

# Tool calls
ax = axes[1, 1]
bars1 = ax.bar(x - width/2, verbose_tools, width, label='Verbose', color=colors_v, alpha=0.85)
bars2 = ax.bar(x + width/2, doclean_tools, width, label='DocLean', color=colors_d, alpha=0.85)
ax.set_ylabel('Tool Calls')
ax.set_title('Number of Tool Calls (File Reads)')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()
for bar, val in zip(bars1, verbose_tools):
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), str(val), ha='center', va='bottom', fontsize=10)
for bar, val in zip(bars2, doclean_tools):
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), str(val), ha='center', va='bottom', fontsize=10)

# Savings annotation
savings_text = "Token Savings: Petstore 14% | Proto-Storage 89% | Snyk 78%\nCost Savings: Petstore 45% | Proto-Storage 79% | Snyk 48%"
fig.text(0.5, 0.01, savings_text, ha='center', fontsize=10, style='italic',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout(rect=[0, 0.06, 1, 0.96])
out_path = '/data/workspace/lap-benchmark-docs/results/batch_20260208_181843/pilot_chart.png'
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f"Chart saved to {out_path}")
