#!/usr/bin/env python3
"""AutoQuality artifact-driven control loop sensor/controller.

This script reads completed AutoQuality comparison artifacts, summarizes the
metric gap, and recommends the next small loop. It never uses labels for blind
scoring. Label-aware recommendations are for post-run evolution only.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


METRIC_KEYS = (
    "accuracy",
    "precision",
    "recall",
    "f1",
    "false_positive_rate",
    "false_negative_rate",
)

DAMPENERS = [
    "No client labels, raw markers, bad: marker tokens, or status-derived fields during blind scoring.",
    "Do not optimize to a fixed REVIEW rate or discard rate.",
    "Every new holdout needs a named exit question and remains REVIEW-only.",
    "Every new DISCARD rule needs hard row evidence and accepted-row counterexamples.",
    "Validate every chunk with validate_agent_judgments.py before accepting the loop.",
    "Compare the new version against the prior version before promoting any learning.",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read AutoQuality run artifacts and recommend the next control-loop action."
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument(
        "--frontier-target",
        type=float,
        default=0.90,
        help="Target used only for reporting metric gaps, not for routing rates.",
    )
    return parser.parse_args()


def version_for(path: Path) -> int | None:
    if path.name == "comparison_results.json":
        return 2
    match = re.fullmatch(r"v(\d+)_comparison_results\.json", path.name)
    if match:
        return int(match.group(1))
    return None


def pct(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value * 100:.1f}%"
    return "n/a"


def as_number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def load_results(run_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("*comparison_results.json")):
        version = version_for(path)
        if version is None:
            continue
        data = json.loads(path.read_text())
        strict = data.get("strict_discard_only", {})
        soft = data.get("soft_discard_or_review", {})
        results.append(
            {
                "version": version,
                "file": str(path),
                "dataset": data.get("dataset"),
                "total_respondents": data.get("total_respondents"),
                "prediction_distribution": data.get("prediction_distribution", {}),
                "strict": {key: strict.get(key) for key in (*METRIC_KEYS, "tp", "fp", "tn", "fn")},
                "soft": {key: soft.get(key) for key in (*METRIC_KEYS, "tp", "fp", "tn", "fn")},
                "extra": {
                    key: value
                    for key, value in data.items()
                    if key
                    not in {
                        "dataset",
                        "total_respondents",
                        "client_distribution",
                        "prediction_distribution",
                        "strict_discard_only",
                        "soft_discard_or_review",
                        "strict_error_analysis",
                        "soft_error_analysis",
                    }
                },
            }
        )
    return sorted(results, key=lambda item: item["version"])


def metric_delta(latest: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    if previous is None:
        return {}
    deltas: dict[str, Any] = {"strict": {}, "soft": {}, "prediction_distribution": {}}
    for mode in ("strict", "soft"):
        for key in METRIC_KEYS:
            deltas[mode][key] = round(
                as_number(latest[mode].get(key)) - as_number(previous[mode].get(key)), 4
            )
        for key in ("tp", "fp", "tn", "fn"):
            deltas[mode][key] = latest[mode].get(key, 0) - previous[mode].get(key, 0)
    latest_dist = latest.get("prediction_distribution", {})
    previous_dist = previous.get("prediction_distribution", {})
    for key in sorted(set(latest_dist) | set(previous_dist)):
        deltas["prediction_distribution"][key] = latest_dist.get(key, 0) - previous_dist.get(key, 0)
    return deltas


def metric_gaps(latest: dict[str, Any], target: float) -> dict[str, dict[str, float]]:
    gaps: dict[str, dict[str, float]] = {"strict": {}, "soft": {}}
    for mode in ("strict", "soft"):
        for key in ("accuracy", "precision", "recall", "f1"):
            gaps[mode][key] = round(max(0.0, target - as_number(latest[mode].get(key))), 4)
    return gaps


def validation_status(run_dir: Path, version: int) -> dict[str, Any]:
    chunk_files = sorted(run_dir.glob(f"agent_judgments_v{version}_chunk_*.json"))
    text_files = [
        run_dir / f"v{version}_run_assessment.md",
        run_dir / f"v{version}_performance_report.md",
        run_dir / "workledger.md",
    ]
    combined = "\n".join(path.read_text(errors="ignore") for path in text_files if path.exists())
    reported_pass = bool(
        re.search(r"All\s+\d+\s+chunks\s+pass", combined, flags=re.IGNORECASE)
        or re.search(r"chunk_00:\s*OK", combined, flags=re.IGNORECASE)
    )
    return {
        "chunk_file_count": len(chunk_files),
        "reported_pass": reported_pass,
        "status": "reported_pass" if reported_pass else "needs_explicit_validation_log",
    }


def choose_action(
    latest: dict[str, Any], previous: dict[str, Any] | None, deltas: dict[str, Any]
) -> tuple[str, list[str], list[str]]:
    strict = latest["strict"]
    soft = latest["soft"]
    strict_precision = as_number(strict.get("precision"))
    strict_recall = as_number(strict.get("recall"))
    soft_f1 = as_number(soft.get("f1"))
    soft_fnr = as_number(soft.get("false_negative_rate"))
    soft_fpr = as_number(soft.get("false_positive_rate"))
    soft_fn = int(soft.get("fn") or 0)

    rationale: list[str] = []
    next_steps: list[str] = []

    if previous is not None:
        strict_fp_delta = deltas["strict"].get("fp", 0)
        strict_precision_delta = deltas["strict"].get("precision", 0.0)
        soft_f1_delta = deltas["soft"].get("f1", 0.0)
        soft_fpr_delta = deltas["soft"].get("false_positive_rate", 0.0)
        if strict_fp_delta > 10 or strict_precision_delta < -0.02:
            return (
                "fp_guardrail",
                [
                    f"Strict false positives increased by {strict_fp_delta}.",
                    f"Strict precision delta is {strict_precision_delta:+.3f}.",
                ],
                [
                    "Compare new DISCARD rows against accepted rows.",
                    "Demote any rule that lacks hard row evidence or accepted-row counterexamples.",
                    "Re-run validation and comparison before any further recall expansion.",
                ],
            )
        if soft_f1_delta < -0.005:
            return (
                "counterexample_update",
                [f"Soft F1 dropped by {soft_f1_delta:+.3f} versus the prior version."],
                [
                    "Find which new REVIEW or DISCARD routes created the drop.",
                    "Add accepted-row counterexamples or revert the failing route.",
                    "Do not add another recall expansion until soft F1 recovers.",
                ],
            )
        if soft_fpr_delta > 0.05 and soft_f1_delta <= 0.0:
            return (
                "fp_guardrail",
                [
                    f"Soft FPR rose by {soft_fpr_delta:+.3f} without a soft-F1 gain.",
                    f"Latest soft FPR is {soft_fpr:.3f}.",
                ],
                [
                    "Mine REVIEW false positives against true REVIEW/soft positives.",
                    "Add exit criteria that moves weak or protected REVIEW rows back to KEEP.",
                    "Keep distribution audit descriptive, not target-driven.",
                ],
            )

    if soft_fnr > 0.20 or soft_fn > 100:
        rationale.extend(
            [
                f"Soft false-negative rate is {soft_fnr:.3f}.",
                f"{soft_fn} client discards remain in KEEP under soft evaluation.",
            ]
        )
        next_steps.extend(
            [
                "Mine latest KEEP false negatives against true keeps using labels only after the blind run.",
                "Prefer specific field/value or cross-field holdouts with accepted-row counterexamples.",
                "Apply surviving signals as REVIEW holdouts with named exit questions, not DISCARD.",
            ]
        )
        return "auto_keep_holdout", rationale, next_steps

    if strict_recall < 0.15 and strict_precision >= 0.55 and soft_f1 >= 0.60:
        rationale.extend(
            [
                f"Strict recall is still {strict_recall:.3f}, while strict precision is {strict_precision:.3f}.",
                f"Soft F1 is {soft_f1:.3f}; the REVIEW lane is now useful enough to mine for hard discard candidates.",
            ]
        )
        next_steps.extend(
            [
                "Mine latest REVIEW true positives against REVIEW false positives using labels only in evolution.",
                "Prioritize cross-field semantic reconstruction over more one-field holdouts.",
                "Promote only hard row-specific failures that survive accepted-row counterexamples.",
                "Simulate candidate DISCARD rules first; accept only if strict precision does not drop materially.",
            ]
        )
        return "discard_candidate_mining", rationale, next_steps

    rationale.extend(
        [
            "No single error bucket crosses the default escalation thresholds.",
            "The next useful work is signal refinement rather than broader routing.",
        ]
    )
    next_steps.extend(
        [
            "Split broad signals into discriminating child signals.",
            "Add counterexamples for any signal with mixed evidence.",
            "Validate on another dataset before promotion.",
        ]
    )
    return "signal_split", rationale, next_steps


def render_metrics_table(results: list[dict[str, Any]]) -> str:
    lines = [
        "| Version | DISCARD | REVIEW | KEEP | Strict P | Strict R | Strict F1 | Soft P | Soft R | Soft F1 | Soft FPR |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        dist = result.get("prediction_distribution", {})
        lines.append(
            "| "
            + " | ".join(
                [
                    f"V{result['version']}",
                    str(dist.get("DISCARD", 0)),
                    str(dist.get("REVIEW", 0)),
                    str(dist.get("KEEP", 0)),
                    pct(result["strict"].get("precision")),
                    pct(result["strict"].get("recall")),
                    pct(result["strict"].get("f1")),
                    pct(result["soft"].get("precision")),
                    pct(result["soft"].get("recall")),
                    pct(result["soft"].get("f1")),
                    pct(result["soft"].get("false_positive_rate")),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def render_report(state: dict[str, Any]) -> str:
    latest = state["latest"]
    previous = state.get("previous")
    latest_label = f"V{latest['version']}"
    previous_label = f"V{previous['version']}" if previous else "none"
    lines = [
        "# AutoQuality control loop report",
        "",
        f"Run directory: `{state['run_dir']}`",
        f"Generated: {state['generated_at_utc']}",
        f"Latest version: {latest_label}",
        f"Compared against: {previous_label}",
        "",
        "## Metric sensor",
        "",
        render_metrics_table(state["versions"]),
        "",
        "## Frontier gaps",
        "",
        f"Reporting target: {state['frontier_target']:.0%}. This target is for metric gap tracking only, not for REVIEW or discard rates.",
        "",
        "| Mode | Accuracy gap | Precision gap | Recall gap | F1 gap |",
        "|---|---:|---:|---:|---:|",
    ]
    for mode in ("strict", "soft"):
        gaps = state["gaps"][mode]
        lines.append(
            "| "
            + " | ".join(
                [
                    mode,
                    pct(gaps["accuracy"]),
                    pct(gaps["precision"]),
                    pct(gaps["recall"]),
                    pct(gaps["f1"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Controller decision",
            "",
            f"Action: `{state['controller_action']}`",
            "",
            "Rationale:",
        ]
    )
    lines.extend(f"- {item}" for item in state["rationale"])
    lines.extend(["", "Next loop instructions:"])
    lines.extend(f"- {item}" for item in state["next_loop_instructions"])
    lines.extend(["", "Dampeners:"])
    lines.extend(f"- {item}" for item in state["dampeners"])
    lines.extend(
        [
            "",
            "## Validation sensor",
            "",
            f"Latest chunk files found: {state['validation']['chunk_file_count']}",
            f"Validation status: `{state['validation']['status']}`",
            "",
            "## Promotion gate",
            "",
            "Promote a learning into the skill only after the next version validates, improves the targeted metric bucket, preserves FP guardrails, and has positive examples plus accepted-row counterexamples.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    output_md = (args.output_md or run_dir / "control_loop_report.md").resolve()
    output_json = (args.output_json or run_dir / "control_loop_state.json").resolve()

    results = load_results(run_dir)
    if not results:
        raise SystemExit(f"No comparison result files found in {run_dir}")

    latest = results[-1]
    previous = results[-2] if len(results) > 1 else None
    deltas = metric_delta(latest, previous)
    gaps = metric_gaps(latest, args.frontier_target)
    action, rationale, next_steps = choose_action(latest, previous, deltas)
    state = {
        "run_dir": str(run_dir),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "frontier_target": args.frontier_target,
        "versions": results,
        "latest": latest,
        "previous": previous,
        "deltas": deltas,
        "gaps": gaps,
        "controller_action": action,
        "rationale": rationale,
        "next_loop_instructions": next_steps,
        "dampeners": DAMPENERS,
        "validation": validation_status(run_dir, latest["version"]),
    }

    output_json.write_text(json.dumps(state, indent=2) + "\n")
    output_md.write_text(render_report(state))
    print(f"Wrote {output_md}")
    print(f"Wrote {output_json}")
    print(f"Latest V{latest['version']} controller action: {action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
