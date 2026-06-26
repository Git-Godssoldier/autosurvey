#!/usr/bin/env python3
"""Phase 1: Run pipeline and produce review packets for agent review.

This script runs ML triage + rule-based scoring, then writes review packets
for all respondents with score < 0 (and optionally all respondents).
The review packets are JSON files designed to be read by LLM subagents.

The subagents produce judgments that are then integrated by integrate_agent_judgments.py.

Usage:
    python3 run_pipeline_with_agent_review.py <xlsx_path> [--output-dir DIR] [--review-all]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add the skills scripts directory
SKILL_SCRIPTS = Path(__file__).parent.parent / "skills" / "cleaning-survey-quality" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from survey_pipeline import (
    extract_features_and_chain,
    ml_triage,
    agent_score_respondent,
    reassess_respondent,
    compute_key_signals,
    run_pipeline,
)


def run_pipeline_with_review_packets(filepath, output_dir=None, review_all=False):
    """Run pipeline and produce review packets for agent review."""
    filepath = Path(filepath)
    if output_dir is None:
        output_dir = filepath.parent / f"{filepath.stem}_quality_output"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run the standard pipeline first (produces Excel + dashboard)
    df = run_pipeline(filepath, output_dir)

    # Now produce review packets for agent review
    print(f"\n[6/7] Producing review packets for agent review...")

    # Re-extract answer chains (they were computed inside run_pipeline)
    # We need them for the review packets
    _, datamap, roles, answer_chains = extract_features_and_chain(filepath)

    # Re-compute scores to get the answer chains aligned
    matrix_prevalence = (df["matrix_straightline"] == 1).mean() if "matrix_straightline" in df.columns else None
    agent_scores = []
    for idx, row in df.iterrows():
        chain = answer_chains[idx] if idx < len(answer_chains) else {}
        score, reasons = agent_score_respondent(chain, row["ml_triage_score"], matrix_prevalence=matrix_prevalence)
        agent_scores.append(score)

    # Select respondents for review
    if review_all:
        review_indices = list(range(len(df)))
    else:
        review_indices = [i for i, s in enumerate(agent_scores) if s < 0]

    print(f"  Respondents to review: {len(review_indices)}")

    # Build review packets
    review_packets = []
    for idx in review_indices:
        row = df.iloc[idx]
        chain = answer_chains[idx] if idx < len(answer_chains) else {}

        # Build a compact but complete review packet
        packet = {
            "respondent_id": row["respondent_id"],
            "ml_triage_score": round(float(row["ml_triage_score"]), 3),
            "rule_based_score": round(float(agent_scores[idx]), 3),
            "supplier": chain.get("supplier", ""),
            "supplier_reject_rate": chain.get("supplier_reject_rate", 0),
            "qtime_minutes": round(chain.get("qtime_minutes", 0), 1),
            "qtime_percentile": chain.get("qtime_percentile", ""),
            "signal_count": chain.get("signal_count", 0),
            "t1_count": chain.get("t1_count", 0),
            "t2_count": chain.get("t2_count", 0),
            "t3_count": chain.get("t3_count", 0),
            "oe_total_chars": chain.get("oe_total_chars", 0),
            "answer_entropy": round(chain.get("answer_entropy", 0), 2),
            "matrix_unique_ratio": round(chain.get("matrix_unique_ratio", 0), 3),
            "matrix_straightline": chain.get("matrix_straightline", 0),
            "oe_dup_count": chain.get("oe_dup_count", 0),
            "ip_dup_count": chain.get("ip_dup_count", 0),
            "lang_readlevel": chain.get("lang_readlevel", 0),
            "oe_text": chain.get("oe_text", ""),
            "key_signals": row["key_signals"] if isinstance(row.get("key_signals"), list) else [],
            "rule_reasons": row["agent_reasons"] if isinstance(row.get("agent_reasons"), list) else [],
            # Include the full answer chain for agent review
            "answer_chain": [
                {
                    "field": a["field"],
                    "question": a["question_text"][:100],
                    "answer": a["label"][:80],
                    "type": a["answer_type"],
                }
                for a in chain.get("answer_chain", [])
            ],
        }
        review_packets.append(packet)

    # Write review packets
    packets_path = output_dir / "review_packets_for_agent.json"
    with open(packets_path, "w") as f:
        json.dump(review_packets, f, indent=2)
    print(f"  Review packets: {packets_path}")

    # Write instructions for the agent
    instructions = f"""# Agent Review Instructions

Read the file `review_packets_for_agent.json`. It contains {len(review_packets)} respondent review packets.

For each respondent, read:
1. The open-end text (oe_text)
2. The answer chain (answer_chain — field, question, answer, type)
3. The signals (key_signals, rule_reasons)
4. The ML triage score and rule-based score

Then assign:
- `agent_score`: -1 to +1 (-1 = clear discard, -0.5 = discard lean, 0 = uncertain, +0.5 = keep lean, +1 = clear keep)
- `agent_judgment`: "DISCARD", "REVIEW", or "KEEP"
- `agent_justification`: 2-3 sentence natural language explanation citing specific answer chain evidence

Write your judgments to `agent_judgments.json` as a JSON array with one entry per respondent:

```json
[
  {{
    "respondent_id": "...",
    "agent_score": -0.7,
    "agent_judgment": "DISCARD",
    "agent_justification": "The open-end text describes what the survey was about in third person ('this survey was about water filtration...') rather than sharing personal experience. Combined with matrix straightlining across all q10 items and missing q14, this respondent shows no genuine engagement."
  }},
  ...
]
```

Key patterns to look for (from prior agent review of this dataset):
- **Third-person meta-description open-ends**: "this survey was about..." or "questions were asked about..." — this is the #1 missed pattern
- **Generic topic restatement**: Mentions water/filtration but no personal experience or first-person language
- **Off-topic or incoherent q14 answers**: "Good night", "i need it", conspiracy theories
- **Missing critical fields**: q14 or other high-value open-ends entirely absent
- **Templated/truncated open-ends**: Phrases that end mid-sentence or follow a copy-paste template
- **Gibberish or nonsense text**: Keyboard mashing or unreadable text

Protective factors (argue for KEEP):
- **First-person personal experience**: "My water tastes bad", "I bought it for my family"
- **Natural misspellings**: "filtation" instead of "filtration" — bots produce correct text
- **Matrix variation**: Different answers across semantically different questions
- **Specific unique details**: Answers that only this respondent would give

All respondents in this file have rule_based_score < 0 (they were flagged for review).
The ML triage score is a risk probability (0-1) — it flags high-risk respondents but is not a standalone classifier.
"""
    instructions_path = output_dir / "agent_review_instructions.md"
    with open(instructions_path, "w") as f:
        f.write(instructions)
    print(f"  Instructions: {instructions_path}")

    print(f"\n[7/7] Next step: Spawn subagents to review {len(review_packets)} packets")
    print(f"  Subagents should read: {packets_path}")
    print(f"  Subagents should write: {output_dir / 'agent_judgments.json'}")
    print(f"  Then run: python3 integrate_agent_judgments.py {filepath} {output_dir}")

    return df, review_packets


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run_pipeline_with_agent_review.py <xlsx_path> [--output-dir DIR] [--review-all]")
        return

    filepath = Path(sys.argv[1])
    output_dir = None
    review_all = False

    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == "--output-dir" and i + 1 < len(sys.argv):
            output_dir = Path(sys.argv[i + 1])
        elif arg == "--review-all":
            review_all = True

    run_pipeline_with_review_packets(filepath, output_dir, review_all)


if __name__ == "__main__":
    main()
