"""
Evaluate trial_log.csv: compare assisted vs teleop_only conditions.
Outputs summary table, t-test results, and per-trial breakdown.

Usage:
    python evaluate.py
"""

import csv
import numpy as np
from scipy import stats

LOG_FILE = "trial_log.csv"

# ---- Load data ----
trials = []
with open(LOG_FILE, "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        trial = {
            "trial": int(row["trial"]),
            "condition": row["condition"],
            "task": row["task"],
            "completion_time": float(row["completion_time"]),
            "path_length": float(row["path_length"]),
            "teleop_inputs": int(row["teleop_inputs"]),
            "success": row.get("success", "").strip(),
            "comments": row.get("comments", "").strip(),
        }
        trials.append(trial)

assisted = [t for t in trials if t["condition"] == "assisted"]
teleop = [t for t in trials if t["condition"] == "teleop_only"]

# ---- Print all trials ----
# print("=" * 90)
# print("ALL TRIALS")
# print("=" * 90)
# header = f"{'#':<4} {'Condition':<14} {'Time(s)':<10} {'Path':<10} {'Inputs':<8} {'Success':<9} {'Task'}"
# print(header)
# print("-" * 90)
# for t in trials:
#     print(f"{t['trial']:<4} {t['condition']:<14} {t['completion_time']:<10} {t['path_length']:<10} {t['teleop_inputs']:<8} {t['success']:<9} {t['task']}")
#     if t["comments"]:
#         print(f"     Comment: {t['comments']}")
# print()

# ---- Summary statistics ----
def summarize(group, label):
    if not group:
        print(f"  No {label} trials found.\n")
        return
    times = [t["completion_time"] for t in group]
    paths = [t["path_length"] for t in group]
    inputs = [t["teleop_inputs"] for t in group]
    success_count = sum(1 for t in group if t["success"] == "True")
    total = len(group)

    print(f"  {label} (n={total}):")
    print(f"    Completion time:  mean={np.mean(times):.2f}s,  std={np.std(times):.2f}s,  min={np.min(times):.2f}s,  max={np.max(times):.2f}s")
    print(f"    Path length:      mean={np.mean(paths):.4f},  std={np.std(paths):.4f}")
    print(f"    Teleop inputs:    mean={np.mean(inputs):.1f},  std={np.std(inputs):.1f}")
    print(f"    Success rate:     {success_count}/{total} ({100*success_count/total:.0f}%)")
    print()

print("=" * 90)
print("SUMMARY STATISTICS")
print("=" * 90)
summarize(assisted, "Assisted")
summarize(teleop, "Teleop Only")

# ---- Statistical tests ----
print("=" * 90)
print("STATISTICAL TESTS (assisted vs teleop_only)")
print("=" * 90)

if len(assisted) >= 2 and len(teleop) >= 2:
    # Independent samples t-test (unequal sample sizes ok)
    a_times = [t["completion_time"] for t in assisted]
    t_times = [t["completion_time"] for t in teleop]
    a_paths = [t["path_length"] for t in assisted]
    t_paths = [t["path_length"] for t in teleop]
    a_inputs = [t["teleop_inputs"] for t in assisted]
    t_inputs = [t["teleop_inputs"] for t in teleop]

    for metric, a_vals, t_vals in [
        ("Completion Time", a_times, t_times),
        ("Path Length", a_paths, t_paths),
        ("Teleop Inputs", a_inputs, t_inputs),
    ]:
        t_stat, p_val = stats.ttest_ind(a_vals, t_vals, equal_var=False)
        sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "n.s."
        print(f"\n  {metric}:")
        print(f"    Assisted mean:    {np.mean(a_vals):.3f}")
        print(f"    Teleop mean:      {np.mean(t_vals):.3f}")
        print(f"    t-statistic:      {t_stat:.4f}")
        print(f"    p-value:          {p_val:.4f}  {sig}")

    # Success rate comparison (Fisher's exact test)
    a_success = sum(1 for t in assisted if t["success"] == "True")
    a_fail = len(assisted) - a_success
    t_success = sum(1 for t in teleop if t["success"] == "True")
    t_fail = len(teleop) - t_success
    _, p_fisher = stats.fisher_exact([[a_success, a_fail], [t_success, t_fail]])
    sig = "***" if p_fisher < 0.001 else "**" if p_fisher < 0.01 else "*" if p_fisher < 0.05 else "n.s."
    print(f"\n  Success Rate (Fisher's exact test):")
    print(f"    Assisted:         {a_success}/{len(assisted)}")
    print(f"    Teleop:           {t_success}/{len(teleop)}")
    print(f"    p-value:          {p_fisher:.4f}  {sig}")
else:
    print("  Not enough data for t-tests (need >= 2 trials per condition).")

# ---- Paired comparison for matching tasks ----
print(f"\n{'=' * 90}")
print("PAIRED TASK COMPARISON (same task, both conditions)")
print("=" * 90)

# # group by task
# from collections import defaultdict
# task_groups = defaultdict(lambda: {"assisted": [], "teleop_only": []})
# for t in trials:
#     task_groups[t["task"]][t["condition"]].append(t)

# paired_a_times = []
# paired_t_times = []
# for task, groups in task_groups.items():
#     if groups["assisted"] and groups["teleop_only"]:
#         a_avg = np.mean([t["completion_time"] for t in groups["assisted"]])
#         t_avg = np.mean([t["completion_time"] for t in groups["teleop_only"]])
#         paired_a_times.append(a_avg)
#         paired_t_times.append(t_avg)
#         print(f"  Task: '{task}'")
#         print(f"    Assisted avg time:  {a_avg:.2f}s (n={len(groups['assisted'])})")
#         print(f"    Teleop avg time:    {t_avg:.2f}s (n={len(groups['teleop_only'])})")
#         print()

# if len(paired_a_times) >= 2:
#     t_stat, p_val = stats.ttest_rel(paired_a_times, paired_t_times)
#     sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "n.s."
#     print(f"  Paired t-test on matching tasks (completion time):")
#     print(f"    t-statistic: {t_stat:.4f}")
#     print(f"    p-value:     {p_val:.4f}  {sig}")
# elif paired_a_times:
#     print("  Only 1 paired task found — need >= 2 for paired t-test.")
# else:
#     print("  No matching tasks found between conditions.")

# print(f"\n{'=' * 90}")
# print("Significance levels: * p<0.05, ** p<0.01, *** p<0.001, n.s. = not significant")
# print("=" * 90)
