"""
render_bug_chart.py — generates docs/employment_status_bug.png, a chart
showing exactly which of the 27 eval cases failed when SENSITIVE_FIELDS
was deliberately emptied (simulating someone forgetting to keep
'employment_status' on the sensitive-fields list). Not part of the test
suite itself — this is a one-off documentation/portfolio chart, built
from the real eval output captured during that exercise.

Run it with:
    python3 tests/render_bug_chart.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from pathlib import Path

GOOD = "#0ca30c"
CRITICAL = "#d03b3b"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#8a8983"
SURFACE = "#fcfcfb"
GRID = "#e4e3de"

# (id, description, passed) — real results from the run with
# SENSITIVE_FIELDS = set() instead of {"employment_status"}
GROUPS = [
    ("Reads", [
        ("R01", "Get an existing worker", True),
        ("R02", "Get a nonexistent worker", True),
        ("R03", "Search with matches", True),
        ("R04", "Search with zero matches", True),
        ("R05", "Get today's daily plan", True),
        ("R06", "List understaffed cells", True),
    ]),
    ("Routine writes", [
        ("W01", "Mark worker present", True),
        ("W02", "Mark worker absent", True),
        ("W03", "Allocate to valid line/cell", True),
        ("W04", "Allocate nonexistent worker", True),
    ]),
    ("Generic update / bypass", [
        ("U01", "Edit skill_level (benign)", True),
        ("U02", "Edit notes (benign)", True),
        ("U03", "Empty updates rejected", True),
        ("U04", "Bypass: sneak total_parts_made", True),
    ]),
    ("Sensitive field (employment_status)", [
        ("S01", "Approved change", False),
        ("S02", "Denied change", False),
        ("S03", "Nonexistent worker", False),
    ]),
    ("Anomaly detection", [
        ("L01", "Reading at baseline", True),
        ("L02", "3x baseline, approved", True),
        ("L03", "3x baseline, denied", True),
        ("L04", "Nonexistent worker", True),
    ]),
    ("terminate_worker", [
        ("T01", "Approved", True),
        ("T02", "Denied", True),
        ("T03", "Nonexistent worker", True),
    ]),
    ("delete_worker", [
        ("D01", "Approved", True),
        ("D02", "Denied", True),
        ("D03", "Nonexistent worker", True),
    ]),
]

rows = []
for group_name, cases in GROUPS:
    for cid, desc, passed in cases:
        rows.append((group_name, cid, desc, passed))

n = len(rows)
fig_height = 0.34 * n + 1.6
fig, ax = plt.subplots(figsize=(9.5, fig_height), dpi=200)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

y = 0
group_boundaries = []
prev_group = None
yticks_group = []
for group_name, cid, desc, passed in rows:
    if group_name != prev_group:
        if prev_group is not None:
            y -= 0.55  # extra gap between groups
        group_boundaries.append((y, group_name))
        prev_group = group_name

    color = GOOD if passed else CRITICAL
    marker = "✓" if passed else "✗"  # check / cross
    label = "PASS" if passed else "FAIL"

    ax.add_patch(Circle((0.42, y), 0.14, facecolor=color, edgecolor="none", zorder=3))
    ax.text(0.42, y, marker, ha="center", va="center", fontsize=8,
             color="white", fontweight="bold", zorder=4)
    ax.text(0.85, y, f"{cid}", ha="left", va="center", fontsize=9.5,
             color=TEXT_PRIMARY, fontweight="bold", family="monospace")
    ax.text(1.55, y, desc, ha="left", va="center", fontsize=9.5, color=TEXT_SECONDARY)
    ax.text(8.65, y, label, ha="right", va="center", fontsize=9, color=TEXT_MUTED,
             fontweight="bold")

    y -= 1

top = 1
bottom = y

# faint group divider lines + group labels on the left margin
for gy, gname in group_boundaries:
    ax.text(-0.15, gy + 0.35, gname.upper(), ha="left", va="bottom",
             fontsize=7.6, color=TEXT_MUTED, fontweight="bold",
             family="sans-serif")
    ax.plot([-0.15, 8.65], [gy + 0.62, gy + 0.62], color=GRID, lw=0.8, zorder=1)

ax.set_xlim(-0.2, 8.8)
ax.set_ylim(bottom - 0.6, top + 0.4)
ax.axis("off")

passed_n = sum(1 for r in rows if r[3])
failed_n = n - passed_n
title = f"Eval run with employment_status removed from SENSITIVE_FIELDS"
subtitle = (f"{passed_n}/{n} passed ({100*passed_n/n:.1f}%)  —  only the 3 cases "
            f"testing the employment_status gate noticed the missing rule")

fig.text(0.06, 0.975, title, fontsize=12.5, fontweight="bold", color=TEXT_PRIMARY, ha="left")
fig.text(0.06, 0.955, subtitle, fontsize=9.5, color=TEXT_SECONDARY, ha="left")

# legend
legend_y = 0.965
fig.patches.append(Circle((0.855, legend_y), 0.006, transform=fig.transFigure,
                            facecolor=GOOD, edgecolor="none"))
fig.text(0.868, legend_y - 0.006, "pass", fontsize=8.5, color=TEXT_SECONDARY, va="center")
fig.patches.append(Circle((0.918, legend_y), 0.006, transform=fig.transFigure,
                            facecolor=CRITICAL, edgecolor="none"))
fig.text(0.931, legend_y - 0.006, "fail", fontsize=8.5, color=TEXT_SECONDARY, va="center")

plt.tight_layout(rect=[0, 0, 1, 0.94])

out_dir = Path(__file__).parent.parent / "docs"
out_dir.mkdir(exist_ok=True)
out_path = out_dir / "employment_status_bug.png"
plt.savefig(out_path, facecolor=SURFACE, bbox_inches="tight")
print(f"wrote {out_path}")
