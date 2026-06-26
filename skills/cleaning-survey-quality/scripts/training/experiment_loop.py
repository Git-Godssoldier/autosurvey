#!/usr/bin/env python3
"""
Autoresearch experiment loop for survey quality ML.

Following the karpathy/autoresearch methodology:
1. Run experiment
2. Log results to results.tsv
3. If F1 improved, keep. If not, revert.
4. Never stop until target reached or human interrupts.

Usage: python3 experiment_loop.py
"""
from __future__ import annotations

import os
import sys
import subprocess
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
RESULTS_TSV = SCRIPTS_DIR.parent / "models" / "results.tsv"
EVAL_HARNESS = SCRIPTS_DIR / "eval_harness.py"

def run_experiment(train_script: str, description: str) -> dict:
    """Run one experiment and return the results."""
    print(f"\n{'='*80}")
    print(f"EXPERIMENT: {description}")
    print(f"Script: {train_script}")
    print(f"{'='*80}")

    t0 = time.time()
    result = subprocess.run(
        [sys.executable, str(EVAL_HARNESS), train_script],
        capture_output=True, text=True, timeout=600
    )
    elapsed = time.time() - t0

    # Extract avg_f1 from output
    avg_f1 = 0.0
    for line in result.stdout.split("\n"):
        if line.startswith("avg_f1:"):
            avg_f1 = float(line.split(":")[1].strip())
            break

    if result.returncode != 0 or avg_f1 == 0.0:
        print(f"CRASH: {result.stderr[-500:]}")
        return {"avg_f1": 0.0, "status": "crash", "description": description, "elapsed": elapsed}

    # Print the output
    print(result.stdout)

    return {"avg_f1": avg_f1, "status": "done", "description": description, "elapsed": elapsed}


def log_result(commit: str, avg_f1: float, status: str, description: str):
    """Log result to results.tsv."""
    exists = RESULTS_TSV.exists()
    with open(RESULTS_TSV, "a") as f:
        if not exists:
            f.write("commit\tavg_f1\tstatus\tdescription\n")
        f.write(f"{commit}\t{avg_f1:.6f}\t{status}\t{description}\n")
    print(f"Logged: {commit}\t{avg_f1:.6f}\t{status}\t{description}")


def get_commit_hash() -> str:
    """Get short git commit hash."""
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, cwd=SCRIPTS_DIR.parent.parent
    )
    return result.stdout.strip() if result.returncode == 0 else "no-git"


if __name__ == "__main__":
    # Run a single experiment
    script = sys.argv[1] if len(sys.argv) > 1 else str(SCRIPTS_DIR / "train_v1_f1.py")
    desc = sys.argv[2] if len(sys.argv) > 2 else "baseline F1-optimal"
    
    result = run_experiment(script, desc)
    commit = get_commit_hash()
    log_result(commit, result["avg_f1"], result["status"], desc)
