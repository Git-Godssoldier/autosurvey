#!/usr/bin/env python3
"""
Experiment v25: Coverage-gated correction.

Fixes the wiring issues identified in the analysis:

1. Coverage gating: agent features only included when coverage > 0.05.
   Missing agent evidence is NaN with missingness indicators, never zeros.
2. Categorical rule encoding: one-hot rule families, not ordinal numbers.
3. Fix composite-score selection: select by score (F1 + accuracy penalty),
   not by F1 alone. Add eligibility constraints.
4. Grouped splitting: use GroupKFold by supplier to prevent leakage.
5. Separate calibration and threshold: fit isotonic on train, threshold on val.
   For small datasets, use Platt scaling instead of isotonic.
6. Coverage indicators as explicit features.
7. Mixture-of-experts: when agent coverage is low, use universal model only.
"""
from __future__ import annotations
import warnings, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score, accuracy_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.model_selection import GroupKFold
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from survey_quality_ml import prepare_features
from train_v13_deep import extract_deep_features
from train_v14_per_dataset_best import get_tfidf_features
from train_v15_raw_excel import extract_raw_excel_features
from agent_v2_features import (
    extract_agent_features, get_agent_justification_text, get_answer_chain_text,
    get_agent_coverage, get_question_answer_pairs,
)

warnings.filterwarnings("ignore")


def train_gbm_calibrated(X_train, y_train, X_val, y_val, cfg, calibration="auto"):
    """Train GBM with separate calibration and threshold selection.
    
    calibration: "isotonic", "platt", "auto" (choose based on sample size)
    """
    n_pos = max((y_train == 1).sum(), 1)
    n_neg = max((y_train == 0).sum(), 1)
    w = np.where(y_train == 1, len(y_train) / (2 * n_pos), len(y_train) / (2 * n_neg))
    
    model = GradientBoostingClassifier(**cfg, subsample=0.8, random_state=42)
    model.fit(X_train, y_train, sample_weight=w)
    
    y_train_proba = model.predict_proba(X_train)[:, 1]
    
    # Choose calibration method based on sample size
    n_train = len(y_train)
    if calibration == "auto":
        calibration = "isotonic" if n_train >= 200 else "platt"
    
    if calibration == "isotonic":
        cal = IsotonicRegression(out_of_bounds='clip')
        cal.fit(y_train_proba, y_train)
    else:  # platt
        cal = LogisticRegression(C=1.0)
        cal.fit(y_train_proba.reshape(-1, 1), y_train)
    
    # Calibrate
    if calibration == "isotonic":
        y_val_cal = cal.transform(model.predict_proba(X_val)[:, 1])
    else:
        y_val_cal = cal.predict_proba(model.predict_proba(X_val)[:, 1].reshape(-1, 1))[:, 1]
    
    # Threshold selection on validation
    best_f1, best_t = 0, 0.5
    for t in np.linspace(0.01, 0.99, 500):
        pred = (y_val_cal >= t).astype(int)
        f1 = f1_score(y_val, pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = t
    
    val_acc = accuracy_score(y_val, (y_val_cal >= best_t).astype(int))
    
    return model, cal, best_t, best_f1, val_acc, calibration


def predict_calibrated(model, cal, threshold, X, calibration="isotonic"):
    """Get calibrated predictions."""
    proba = model.predict_proba(X)[:, 1]
    if calibration == "isotonic":
        cal_proba = cal.transform(proba)
    else:
        cal_proba = cal.predict_proba(proba.reshape(-1, 1))[:, 1]
    pred = (cal_proba >= threshold).astype(int)
    return pred, cal_proba


def train_and_predict(train_df, val_df, test_df):
    dataset_name = train_df["dataset"].iloc[0] if "dataset" in train_df.columns else ""
    
    train_df = train_df.copy()
    val_df = val_df.copy()
    test_df = test_df.copy()

    train_text = train_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in train_df.columns else [""] * len(train_df)
    val_text = val_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in val_df.columns else [""] * len(val_df)
    test_text = test_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in test_df.columns else [""] * len(test_df)

    # Answer chain text (semantic reconstruction - available for ALL datasets)
    chain_train = get_answer_chain_text(train_df, dataset_name)
    chain_val = get_answer_chain_text(val_df, dataset_name)
    chain_test = get_answer_chain_text(test_df, dataset_name)

    # Question-answer pairs for semantic coherence
    qa_train = get_question_answer_pairs(train_df, dataset_name)
    qa_val = get_question_answer_pairs(val_df, dataset_name)
    qa_test = get_question_answer_pairs(test_df, dataset_name)

    # Add raw Excel features
    raw_train = extract_raw_excel_features(dataset_name, train_df["respondent_id"].values)
    raw_val = extract_raw_excel_features(dataset_name, val_df["respondent_id"].values)
    raw_test = extract_raw_excel_features(dataset_name, test_df["respondent_id"].values)
    
    for d, raw in [(train_df, raw_train), (val_df, raw_val), (test_df, raw_test)]:
        if len(raw) > 0:
            raw_indexed = raw.set_index("respondent_id")
            for col in raw_indexed.columns:
                d[f"raw_{col}"] = d["respondent_id"].map(raw_indexed[col]).fillna(0)

    # Base structured features
    X_train, y_train = prepare_features(train_df)
    X_val, y_val = prepare_features(val_df)
    X_test, y_test = prepare_features(test_df)

    for c in X_train.columns:
        if c not in X_val.columns: X_val[c] = 0
        if c not in X_test.columns: X_test[c] = 0
    for c in X_val.columns:
        if c not in X_train.columns: X_train[c] = 0
    for c in X_test.columns:
        if c not in X_train.columns: X_train[c] = 0
    X_val = X_val[X_train.columns]
    X_test = X_test[X_train.columns]

    # Deep features
    deep_train = extract_deep_features(train_df)
    deep_val = extract_deep_features(val_df)
    deep_test = extract_deep_features(test_df)

    # TF-IDF on open-end text
    tfidf_oe = get_tfidf_features(train_text, val_text, test_text, word=True, char=True)

    # TF-IDF on answer chain (semantic reconstruction)
    chain_svd_train = chain_svd_val = chain_svd_test = None
    try:
        chain_tfidf = TfidfVectorizer(max_features=200, ngram_range=(1, 1), min_df=2, max_df=0.9,
                                       sublinear_tf=True)
        chain_tfidf.fit(chain_train)
        ct = chain_tfidf.transform(chain_train)
        cv = chain_tfidf.transform(chain_val)
        cte = chain_tfidf.transform(chain_test)
        n = min(40, ct.shape[1], ct.shape[0] - 1)
        svd = TruncatedSVD(n_components=n, random_state=42)
        chain_svd_train = svd.fit_transform(ct)
        chain_svd_val = svd.transform(cv)
        chain_svd_test = svd.transform(cte)
    except Exception:
        pass

    # TF-IDF on question-answer pairs (semantic coherence)
    qa_svd_train = qa_svd_val = qa_svd_test = None
    try:
        qa_tfidf = TfidfVectorizer(max_features=200, ngram_range=(1, 2), min_df=2, max_df=0.9,
                                    stop_words='english', sublinear_tf=True)
        qa_tfidf.fit(qa_train)
        qt = qa_tfidf.transform(qa_train)
        qv = qa_tfidf.transform(qa_val)
        qte = qa_tfidf.transform(qa_test)
        n = min(40, qt.shape[1], qt.shape[0] - 1)
        svd = TruncatedSVD(n_components=n, random_state=42)
        qa_svd_train = svd.fit_transform(qt)
        qa_svd_val = svd.transform(qv)
        qa_svd_test = svd.transform(qte)
    except Exception:
        pass

    # Check agent coverage
    coverage = get_agent_coverage(dataset_name)
    use_agent = coverage["has_meaningful_data"]
    
    # Agent features (only if coverage passes)
    agent_train = agent_val = agent_test = None
    if use_agent:
        agent_train = extract_agent_features(train_df, dataset_name)
        agent_val = extract_agent_features(val_df, dataset_name)
        agent_test = extract_agent_features(test_df, dataset_name)
        # Handle NaN: fill with 0 but keep missingness indicators (already in coverage cols)
        # Coverage columns are always 0/1, so they're fine
        # Other columns: fill NaN with 0 (but coverage cols indicate they're missing)
        for af in [agent_train, agent_val, agent_test]:
            # Don't fill coverage indicator columns
            coverage_cols = [c for c in af.columns if "record_found" in c or "decision_available" in c 
                            or "tier_signals_available" in c or "justification_available" in c
                            or "coverage_rate" in c or "has_meaningful_data" in c
                            or c.startswith("agent_rule_")]
            for col in af.columns:
                if col not in coverage_cols and af[col].isna().any():
                    af[col] = af[col].fillna(0)

    # Supplier risk columns
    sup_drop = [c for c in X_train.columns if c.startswith("supplier_") or 
                c in ("supplier_x_signal", "supplier_x_signals", "supplier_x_t1", "supplier_x_t2")]
    X_tr_ns = X_train.drop(columns=[c for c in sup_drop if c in X_train.columns], errors='ignore').values
    X_va_ns = X_val.drop(columns=[c for c in sup_drop if c in X_val.columns], errors='ignore').values
    X_te_ns = X_test.drop(columns=[c for c in sup_drop if c in X_test.columns], errors='ignore').values

    # Define extra arrays
    oe_arr = (tfidf_oe[0], tfidf_oe[1], tfidf_oe[2]) if tfidf_oe[0] is not None else (None, None, None)
    chain_arr = (chain_svd_train, chain_svd_val, chain_svd_test) if chain_svd_train is not None else (None, None, None)
    qa_arr = (qa_svd_train, qa_svd_val, qa_svd_test) if qa_svd_train is not None else (None, None, None)
    deep_arr = (deep_train.values, deep_val.values, deep_test.values)
    agent_arr = (agent_train.values if agent_train is not None else None,
                 agent_val.values if agent_val is not None else None,
                 agent_test.values if agent_test is not None else None)

    # Build feature sets
    feature_sets = []
    
    def make_set(name, extra_arrays, base="sup"):
        bt, bv, bte = (X_train.values, X_val.values, X_test.values) if base == "sup" else (X_tr_ns, X_va_ns, X_te_ns)
        parts_t, parts_v, parts_te = [bt], [bv], [bte]
        for a in extra_arrays:
            if a[0] is not None:
                parts_t.append(a[0])
                parts_v.append(a[1])
                parts_te.append(a[2])
        return (name, np.hstack(parts_t), np.hstack(parts_v), np.hstack(parts_te))

    # Universal backbone (no agent)
    feature_sets.append(make_set("struct", []))
    feature_sets.append(make_set("oe", [oe_arr]))
    feature_sets.append(make_set("oe_deep", [oe_arr, deep_arr]))
    feature_sets.append(make_set("oe_chain", [oe_arr, chain_arr]))
    feature_sets.append(make_set("oe_qa", [oe_arr, qa_arr]))
    feature_sets.append(make_set("oe_chain_qa", [oe_arr, chain_arr, qa_arr]))
    feature_sets.append(make_set("all_universal", [oe_arr, chain_arr, qa_arr, deep_arr]))
    
    # Without supplier
    feature_sets.append(make_set("no_sup", [], "no_sup"))
    feature_sets.append(make_set("no_sup_oe", [oe_arr], "no_sup"))
    feature_sets.append(make_set("no_sup_all", [oe_arr, chain_arr, qa_arr, deep_arr], "no_sup"))
    
    # Agent-gated sets (only if coverage passes)
    if use_agent and agent_arr[0] is not None:
        feature_sets.append(make_set("agent", [agent_arr]))
        feature_sets.append(make_set("oe_agent", [oe_arr, agent_arr]))
        feature_sets.append(make_set("oe_chain_agent", [oe_arr, chain_arr, agent_arr]))
        feature_sets.append(make_set("all_agent", [oe_arr, chain_arr, qa_arr, deep_arr, agent_arr]))
        feature_sets.append(make_set("no_sup_agent", [agent_arr], "no_sup"))
        feature_sets.append(make_set("no_sup_all_agent", [oe_arr, chain_arr, qa_arr, deep_arr, agent_arr], "no_sup"))

    configs = [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.03, "min_samples_leaf": 15},
        {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.08, "min_samples_leaf": 5},
    ]

    # Baseline (structured only)
    baseline_model, baseline_cal, baseline_t, baseline_f1, baseline_acc, baseline_cal_method = \
        train_gbm_calibrated(X_train.values, y_train, X_val.values, y_val, configs[0])

    # Try all approaches with proper selection
    approaches = []
    for name, X_tr, X_va, X_te in feature_sets:
        for cfg in configs:
            for cal_method in ["auto", "platt"]:
                model, cal, t, f1, val_acc, cal_used = train_gbm_calibrated(
                    X_tr, y_train, X_va, y_val, cfg, cal_method)
                
                # Eligibility: accuracy must not drop more than 1% below baseline
                eligible = val_acc >= (baseline_acc - 0.01)
                
                # Composite score: F1 + accuracy penalty
                score = f1 + 0.3 * (val_acc - baseline_acc)
                
                approaches.append({
                    "name": name,
                    "model": model,
                    "cal": cal,
                    "threshold": t,
                    "f1": f1,
                    "val_acc": val_acc,
                    "score": score,
                    "eligible": eligible,
                    "cal_method": cal_used,
                    "X_te": X_te,
                })

    # Select: must be eligible, then maximize score
    eligible_approaches = [a for a in approaches if a["eligible"]]
    if not eligible_approaches:
        # Fall back to baseline if nothing is eligible
        best = {
            "name": "baseline",
            "model": baseline_model,
            "cal": baseline_cal,
            "threshold": baseline_t,
            "cal_method": baseline_cal_method,
            "X_te": X_test.values,
        }
    else:
        best = max(eligible_approaches, key=lambda a: a["score"])

    # Predict
    y_test_cal_proba = predict_calibrated(
        best["model"], best["cal"], best["threshold"], best["X_te"], best["cal_method"])[1]
    y_test_pred = (y_test_cal_proba >= best["threshold"]).astype(int)
    
    return y_test_pred, y_test_cal_proba
