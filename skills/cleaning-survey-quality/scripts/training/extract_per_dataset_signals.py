#!/usr/bin/env python3
"""Extract per-dataset strongest signals from ML model.

Trains a separate model on each dataset (in-dataset) to find which features
are most predictive for THAT dataset, then also runs LODO to find which
features generalize. Outputs a structured report for the skill.
"""
from __future__ import annotations

import json
import pickle
import re
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent))
from survey_quality_ml import (
    ANNOTATED_DIR, DATASET_MAP, load_signal_map,
    extract_features_from_excel, add_supplier_risk, prepare_features,
    ALL_SIGNALS, T1_SIGNALS, T2_SIGNALS,
)

OUTPUT_DIR = Path(__file__).parent.parent / "references"


def train_per_dataset_importance():
    """Train a model on each dataset individually to find strongest signals."""
    signal_map = load_signal_map()
    all_results = {}

    for fname in sorted(DATASET_MAP.keys()):
        fp = ANNOTATED_DIR / fname
        if not fp.exists():
            continue

        df, _ = extract_features_from_excel(fp, signal_map)
        if df is None or len(df) < 50:
            continue

        n_rej = (df["label"] == 1).sum()
        n_acc = (df["label"] == 0).sum()
        if n_rej < 10 or n_acc < 10:
            print(f"  SKIP {fname}: too few samples ({n_rej} rej, {n_acc} acc)")
            continue

        # Add supplier risk (within-dataset)
        df, _ = add_supplier_risk(df)

        X, y = prepare_features(df)
        if y is None or y.nunique() < 2:
            continue

        # Class weights
        n_pos = max((y == 1).sum(), 1)
        n_neg = max((y == 0).sum(), 1)
        w = np.where(y == 1, len(y) / (2 * n_pos), len(y) / (2 * n_neg))

        # Train
        model = GradientBoostingClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.1,
            subsample=0.8, random_state=42, min_samples_leaf=10
        )
        model.fit(X, y, sample_weight=w)

        # Get feature importances
        importances = model.feature_importances_
        feat_imp = sorted(zip(X.columns, importances), key=lambda x: -x[1])

        # Also get per-feature discrimination: mean(rejected) vs mean(accepted)
        discrimination = []
        for col in X.columns:
            rej_vals = X.loc[y == 1, col]
            acc_vals = X.loc[y == 0, col]
            if rej_vals.std() + acc_vals.std() > 0:
                # Effect size (Cohen's d)
                pooled_std = np.sqrt((rej_vals.std()**2 + acc_vals.std()**2) / 2)
                if pooled_std > 0:
                    d = (rej_vals.mean() - acc_vals.mean()) / pooled_std
                else:
                    d = 0
            else:
                d = 0
            discrimination.append((col, d, float(rej_vals.mean()), float(acc_vals.mean())))

        discrimination.sort(key=lambda x: -abs(x[1]))

        # AUC
        from sklearn.metrics import roc_auc_score
        y_proba = model.predict_proba(X)[:, 1]
        auc = roc_auc_score(y, y_proba)

        # Top signals by importance
        top_imp = feat_imp[:20]
        # Top signals by discrimination
        top_disc = discrimination[:20]

        all_results[fname] = {
            "n_respondents": len(df),
            "n_rejected": int(n_rej),
            "n_accepted": int(n_acc),
            "reject_rate": float(n_rej / len(df)),
            "auc": float(auc),
            "top_features_by_importance": [
                {"feature": f, "importance": float(i)} for f, i in top_imp
            ],
            "top_features_by_discrimination": [
                {
                    "feature": f,
                    "effect_size_cohens_d": float(d),
                    "mean_rejected": float(mr),
                    "mean_accepted": float(ma),
                    "direction": "higher_in_rejected" if d > 0 else "lower_in_rejected",
                }
                for f, d, mr, ma in top_disc
            ],
        }

        print(f"\n{fname}")
        print(f"  N={len(df)}, Rejected={n_rej} ({n_rej/len(df):.1%}), AUC={auc:.3f}")
        print(f"  Top 10 by importance:")
        for f, i in top_imp[:10]:
            print(f"    {f}: {i:.4f}")
        print(f"  Top 10 by discrimination (Cohen's d):")
        for f, d, mr, ma in top_disc[:10]:
            direction = "↑" if d > 0 else "↓"
            print(f"    {direction} {f}: d={d:.3f} (rej={mr:.3f}, acc={ma:.3f})")

    return all_results


def generate_skill_reference(all_results):
    """Generate a markdown reference file for the skill."""
    lines = [
        "# Per-Dataset Strongest ML Signals",
        "",
        "This reference documents the strongest predictive signals for each of the 11 annotated datasets,",
        "extracted from per-dataset Gradient Boosting models. The agent should use these as a starting",
        "point for independent analysis — they tell the agent WHICH signals matter most for EACH dataset,",
        "not what to conclude. The agent must still verify the signal against the respondent's full chain.",
        "",
        "## How to Use",
        "",
        "1. When analyzing a new dataset, first check if it resembles one of the 11 training datasets",
        "   (same client, same survey type, similar reject rate).",
        "2. Use the top features for the most similar dataset as priority signals to check.",
        "3. For each flagged respondent, verify the signal by reading the full answer chain.",
        "4. The effect size (Cohen's d) tells you HOW differently rejected vs accepted respondents",
        "   score on that feature. Large positive d = rejected respondents score much higher.",
        "5. Feature importance tells you how much the model RELIED on that feature for classification.",
        "",
        "## Signal Interpretation Guide",
        "",
        "- `supplier_reject_rate`: Historical reject rate for this supplier. Higher = riskier supplier.",
        "- `rd_RD_Searchr1/r3`: Decipher review metadata. Non-zero = flagged by platform review.",
        "- `qtime_seconds` / `qtime_seconds_zscore`: Completion time. Low z-score = very fast.",
        "- `matrix_unique_ratio`: Diversity of matrix/grid answers. Low = straightlining.",
        "- `oe_*`: Open-end text features. Short/generic/none = low effort.",
        "- `signal_count`: Total client signals. Higher = more quality flags.",
        "- `lang_LangAssess*`: NLP readability scores. Abnormal = suspicious.",
        "- `supplier_x_signals`: Interaction — risky supplier with many signals.",
        "- `coded_dk_ratio`: Proportion of \"don't know\" answers. High = disengaged.",
        "",
        "---",
        "",
    ]

    for fname, data in sorted(all_results.items()):
        lines.extend([
            f"## {fname}",
            "",
            f"- **Respondents**: {data['n_respondents']}",
            f"- **Rejected**: {data['n_rejected']} ({data['reject_rate']:.1%})",
            f"- **In-dataset AUC**: {data['auc']:.3f}",
            "",
            "### Top Features by Model Importance",
            "",
            "| Rank | Feature | Importance |",
            "|------|---------|------------|",
        ])

        for i, feat in enumerate(data["top_features_by_importance"][:15], 1):
            lines.append(f"| {i} | `{feat['feature']}` | {feat['importance']:.4f} |")

        lines.extend([
            "",
            "### Top Features by Discrimination (Cohen's d)",
            "",
            "Effect size: how differently rejected vs accepted respondents score.",
            "Positive d = rejected score HIGHER. Negative d = rejected score LOWER.",
            "",
            "| Rank | Feature | Cohen's d | Direction | Rejected Mean | Accepted Mean |",
            "|------|---------|-----------|-----------|---------------|---------------|",
        ])

        for i, feat in enumerate(data["top_features_by_discrimination"][:15], 1):
            lines.append(
                f"| {i} | `{feat['feature']}` | {feat['effect_size_cohens_d']:.3f} | "
                f"{feat['direction']} | {feat['mean_rejected']:.4f} | {feat['mean_accepted']:.4f} |"
            )

        lines.extend([
            "",
            "### Agent Analysis Notes",
            "",
        ])

        # Auto-generate analysis notes based on the top features
        top_imp_feats = [f["feature"] for f in data["top_features_by_importance"][:5]]
        top_disc_feats = [(f["feature"], f["effect_size_cohens_d"], f["direction"]) 
                          for f in data["top_features_by_discrimination"][:5]]

        notes = []

        # Check for timing signals
        if any("qtime" in f for f in top_imp_feats):
            disc = next((d for f, d, _ in top_disc_feats if "qtime" in f), None)
            if disc is not None and disc < 0:
                notes.append(f"- **Fast completion is a strong signal**: Rejected respondents complete much faster (Cohen's d={abs(disc):.2f}). Check qtime z-score < -1.0.")
            elif disc is not None and disc > 0:
                notes.append(f"- **Slow completion is a signal**: Rejected respondents take longer (Cohen's d={disc:.2f}). May indicate bot-like or stalling behavior.")

        # Check for supplier signals
        if any("supplier" in f for f in top_imp_feats):
            notes.append("- **Supplier risk matters**: The supplier's historical reject rate is a top predictor. Flag respondents from high-risk suppliers for closer review.")

        # Check for matrix signals
        if any("matrix" in f for f in top_imp_feats):
            disc = next((d for f, d, _ in top_disc_feats if "matrix" in f), None)
            if disc is not None and disc < 0:
                notes.append(f"- **Matrix straightlining is predictive**: Rejected respondents have lower matrix diversity (Cohen's d={abs(disc):.2f}). Check matrix_unique_ratio < 0.3.")

        # Check for open-end signals
        if any("oe_" in f for f in top_imp_feats):
            oe_feats = [f for f in top_imp_feats if "oe_" in f]
            notes.append(f"- **Open-end text quality is predictive**: Top OE features: {', '.join(oe_feats[:3])}. Check for short, generic, or missing open-ends.")

        # Check for RD_Search signals
        if any("rd_" in f for f in top_imp_feats):
            notes.append("- **RD_Search metadata is predictive**: Decipher review flags correlate with rejection. Check rd_RD_Searchr1 and rd_RD_Searchr3 values.")

        # Check for signal count
        if any("signal" in f for f in top_imp_feats):
            notes.append("- **Client signal count is predictive**: Respondents with more client signals are more likely rejected.")

        # Check for LangAssess
        if any("lang_" in f for f in top_imp_feats):
            notes.append("- **LangAssess NLP scores are predictive**: Abnormal readability or language scores correlate with rejection.")

        # Check for coded diversity
        if any("coded" in f for f in top_imp_feats):
            notes.append("- **Coded answer diversity matters**: Check for high 'don't know' ratios or low answer diversity.")

        # Check for duplicates
        if any("dup" in f for f in top_imp_feats):
            notes.append("- **Cross-respondent duplicates are predictive**: Check for duplicate open-end text, IP addresses, or user agents.")

        if not notes:
            notes.append("- No single signal dominates. Use the full feature profile for this dataset.")

        # Add reject rate context
        rr = data["reject_rate"]
        if rr > 0.30:
            notes.append(f"- **High reject rate ({rr:.0%})**: This dataset has aggressive cleaning. Many signals may be needed to match.")
        elif rr < 0.10:
            notes.append(f"- **Low reject rate ({rr:.0%})**: This dataset has conservative cleaning. Be very precise — false positives are costly.")
        else:
            notes.append(f"- **Moderate reject rate ({rr:.0%})**: Standard cleaning threshold.")

        lines.extend(notes)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    print("Extracting per-dataset strongest signals...")
    results = train_per_dataset_importance()

    # Save JSON
    json_path = OUTPUT_DIR / "per_dataset_ml_signals.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nJSON saved to {json_path}")

    # Generate markdown
    md = generate_skill_reference(results)
    md_path = OUTPUT_DIR / "per-dataset-ml-signals.md"
    with open(md_path, "w") as f:
        f.write(md)
    print(f"Markdown saved to {md_path}")

    print(f"\nProcessed {len(results)} datasets")


if __name__ == "__main__":
    main()
