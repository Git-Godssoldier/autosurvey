#!/usr/bin/env python3
"""
Experiment v29: Selective classifier with REVIEW band.

Instead of binary discard/keep, introduces a three-way decision:
- DISCARD: p >= discard_threshold (high confidence discard)
- REVIEW:  keep_threshold < p < discard_threshold (uncertain, send to agent)
- KEEP:    p <= keep_threshold (high confidence keep)

The key insight: by introducing a REVIEW band, we can:
1. Set a higher discard threshold → higher precision on auto-discards
2. Set a lower keep threshold → the REVIEW band captures uncertain cases
3. The agent reviews REVIEW cases and makes final determination

For evaluation, we compute F1 two ways:
- Auto F1: only counting auto-DISCARD decisions (high precision)
- Full F1: counting auto-DISCARD + REVIEW-to-DISCARD (full recall)

The evaluation harness expects binary predictions, so we optimize:
- If REVIEW is available: auto-DISCARD for high-confidence, KEEP for low-risk,
  and REVIEW cases get the model's best guess (since we can't actually review)
- The threshold optimization targets F1 with a penalty for REVIEW volume

We also implement dataset-specific threshold shrinkage:
- For datasets with few validation samples, shrink toward global threshold
"""
from __future__ import annotations
import warnings, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score, accuracy_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from survey_quality_ml import prepare_features
from train_v13_deep import extract_deep_features
from train_v14_per_dataset_best import get_tfidf_features
from train_v15_raw_excel import extract_raw_excel_features
from train_v26_universal import extract_packet_features, train_gbm_calibrated, predict_calibrated
from agent_v2_features import get_answer_chain_text, get_question_answer_pairs

warnings.filterwarnings("ignore")


def optimize_selective_thresholds(y_val, val_proba, baseline_acc, review_penalty=0.15):
    """Optimize discard and keep thresholds for selective classification.
    
    Objective: maximize F1 on auto-discards while penalizing REVIEW volume.
    
    The idea: 
    - discard_threshold: above this = DISCARD
    - keep_threshold: below this = KEEP
    - between = REVIEW (uncertain)
    
    For evaluation, REVIEW cases get probability-based guess.
    But we penalize REVIEW volume to encourage confident decisions.
    """
    best_score = -1
    best_dt = 0.5
    best_kt = 0.5
    
    # Search over discard and keep thresholds
    for dt in np.linspace(0.3, 0.95, 50):
        for kt in np.linspace(0.05, 0.5, 30):
            if kt >= dt:
                continue
            
            # Classify
            pred = np.zeros(len(y_val))
            review_mask = (val_proba > kt) & (val_proba < dt)
            discard_mask = val_proba >= dt
            
            # Auto-discards
            pred[discard_mask] = 1
            # REVIEW cases: use probability > 0.5 as guess
            review_pred = (val_proba[review_mask] >= 0.5).astype(int)
            pred[review_mask] = review_pred
            
            f1 = f1_score(y_val, pred, zero_division=0)
            acc = accuracy_score(y_val, pred)
            review_rate = review_mask.mean()
            
            # Penalize REVIEW volume and require accuracy
            if acc < baseline_acc - 0.02:
                continue
            
            score = f1 - review_penalty * review_rate
            if score > best_score:
                best_score = score
                best_dt = dt
                best_kt = kt
    
    return best_dt, best_kt, best_score


def train_and_predict(train_df, val_df, test_df):
    dataset_name = train_df["dataset"].iloc[0] if "dataset" in train_df.columns else ""
    
    train_df = train_df.copy()
    val_df = val_df.copy()
    test_df = test_df.copy()

    train_text = train_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in train_df.columns else [""] * len(train_df)
    val_text = val_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in val_df.columns else [""] * len(val_df)
    test_text = test_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in test_df.columns else [""] * len(test_df)

    chain_train = get_answer_chain_text(train_df, dataset_name)
    chain_val = get_answer_chain_text(val_df, dataset_name)
    chain_test = get_answer_chain_text(test_df, dataset_name)

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

    pkt_train = extract_packet_features(train_df, dataset_name)
    pkt_val = extract_packet_features(val_df, dataset_name)
    pkt_test = extract_packet_features(test_df, dataset_name)

    deep_train = extract_deep_features(train_df)
    deep_val = extract_deep_features(val_df)
    deep_test = extract_deep_features(test_df)

    tfidf_oe = get_tfidf_features(train_text, val_text, test_text, word=True, char=True)

    chain_svd_train = chain_svd_val = chain_svd_test = None
    try:
        chain_tfidf = TfidfVectorizer(max_features=200, ngram_range=(1, 1), min_df=2, max_df=0.9, sublinear_tf=True)
        chain_tfidf.fit(chain_train)
        ct, cv, cte = chain_tfidf.transform(chain_train), chain_tfidf.transform(chain_val), chain_tfidf.transform(chain_test)
        n = min(40, ct.shape[1], ct.shape[0] - 1)
        svd = TruncatedSVD(n_components=n, random_state=42)
        chain_svd_train = svd.fit_transform(ct); chain_svd_val = svd.transform(cv); chain_svd_test = svd.transform(cte)
    except Exception:
        pass

    qa_svd_train = qa_svd_val = qa_svd_test = None
    try:
        qa_tfidf = TfidfVectorizer(max_features=200, ngram_range=(1, 2), min_df=2, max_df=0.9,
                                    stop_words='english', sublinear_tf=True)
        qa_tfidf.fit(qa_train)
        qt, qv, qte = qa_tfidf.transform(qa_train), qa_tfidf.transform(qa_val), qa_tfidf.transform(qa_test)
        n = min(40, qt.shape[1], qt.shape[0] - 1)
        svd = TruncatedSVD(n_components=n, random_state=42)
        qa_svd_train = svd.fit_transform(qt); qa_svd_val = svd.transform(qv); qa_svd_test = svd.transform(qte)
    except Exception:
        pass

    sup_drop = [c for c in X_train.columns if c.startswith("supplier_") or c in ("supplier_x_signal", "supplier_x_signals", "supplier_x_t1", "supplier_x_t2")]
    X_tr_ns = X_train.drop(columns=[c for c in sup_drop if c in X_train.columns], errors='ignore').values
    X_va_ns = X_val.drop(columns=[c for c in sup_drop if c in X_val.columns], errors='ignore').values
    X_te_ns = X_test.drop(columns=[c for c in sup_drop if c in X_test.columns], errors='ignore').values

    oe_arr = (tfidf_oe[0], tfidf_oe[1], tfidf_oe[2]) if tfidf_oe[0] is not None else (None, None, None)
    pkt_arr = (pkt_train.values, pkt_val.values, pkt_test.values)
    chain_arr = (chain_svd_train, chain_svd_val, chain_svd_test) if chain_svd_train is not None else (None, None, None)
    qa_arr = (qa_svd_train, qa_svd_val, qa_svd_test) if qa_svd_train is not None else (None, None, None)
    deep_arr = (deep_train.values, deep_val.values, deep_test.values)

    def make_set(name, extra_arrays, base="sup"):
        bt, bv, bte = (X_train.values, X_val.values, X_test.values) if base == "sup" else (X_tr_ns, X_va_ns, X_te_ns)
        parts_t, parts_v, parts_te = [bt], [bv], [bte]
        for a in extra_arrays:
            if a[0] is not None:
                parts_t.append(a[0]); parts_v.append(a[1]); parts_te.append(a[2])
        return (name, np.hstack(parts_t), np.hstack(parts_v), np.hstack(parts_te))

    feature_sets = [
        make_set("struct", []),
        make_set("pkt", [pkt_arr]),
        make_set("oe", [oe_arr]),
        make_set("oe_pkt", [oe_arr, pkt_arr]),
        make_set("oe_pkt_deep", [oe_arr, pkt_arr, deep_arr]),
        make_set("oe_pkt_chain", [oe_arr, pkt_arr, chain_arr]),
        make_set("oe_pkt_qa", [oe_arr, pkt_arr, qa_arr]) if qa_arr[0] is not None else None,
        make_set("all", [oe_arr, pkt_arr, chain_arr, qa_arr, deep_arr]) if qa_arr[0] is not None else None,
        make_set("no_sup", [], "no_sup"),
        make_set("no_sup_pkt", [pkt_arr], "no_sup"),
        make_set("no_sup_oe_pkt", [oe_arr, pkt_arr], "no_sup"),
        make_set("no_sup_all", [oe_arr, pkt_arr, chain_arr, qa_arr, deep_arr], "no_sup") if qa_arr[0] is not None else None,
    ]
    feature_sets = [s for s in feature_sets if s is not None]

    configs = [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.03, "min_samples_leaf": 15},
        {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.08, "min_samples_leaf": 5},
    ]

    baseline_model, baseline_cal, baseline_t, baseline_f1, baseline_acc, baseline_cal_method = \
        train_gbm_calibrated(X_train.values, y_train, X_val.values, y_val, configs[0])

    approaches = []
    for name, X_tr, X_va, X_te in feature_sets:
        for cfg in configs:
            for cal_method in ["auto", "platt"]:
                model, cal, _, _, val_acc_raw, cal_used = train_gbm_calibrated(
                    X_tr, y_train, X_va, y_val, cfg, cal_method)
                
                # Get calibrated probabilities
                _, val_proba = predict_calibrated(model, cal, 0.5, X_va, cal_used)
                
                # Optimize selective thresholds
                dt, kt, selective_score = optimize_selective_thresholds(
                    y_val, val_proba, baseline_acc, review_penalty=0.15)
                
                # Compute F1 with selective thresholds
                pred = np.zeros(len(y_val))
                review_mask = (val_proba > kt) & (val_proba < dt)
                discard_mask = val_proba >= dt
                pred[discard_mask] = 1
                pred[review_mask] = (val_proba[review_mask] >= 0.5).astype(int)
                f1 = f1_score(y_val, pred, zero_division=0)
                acc = accuracy_score(y_val, pred)
                
                eligible = acc >= (baseline_acc - 0.02)
                score = f1 + 0.3 * (acc - baseline_acc)
                
                approaches.append({
                    "name": name, "model": model, "cal": cal,
                    "discard_t": dt, "keep_t": kt,
                    "f1": f1, "val_acc": acc, "score": score,
                    "eligible": eligible, "cal_method": cal_used,
                    "X_te": X_te,
                })

    eligible_approaches = [a for a in approaches if a["eligible"]]
    if not eligible_approaches:
        # Use baseline with simple threshold
        _, test_proba = predict_calibrated(baseline_model, baseline_cal, 0.5, X_test.values, baseline_cal_method)
        y_test_pred = (test_proba >= baseline_t).astype(int)
        return y_test_pred, test_proba

    best = max(eligible_approaches, key=lambda a: a["score"])
    
    # Predict with selective thresholds
    _, test_proba = predict_calibrated(best["model"], best["cal"], 0.5, best["X_te"], best["cal_method"])
    
    # Apply selective classification
    y_test_pred = np.zeros(len(test_proba))
    review_mask = (test_proba > best["keep_t"]) & (test_proba < best["discard_t"])
    discard_mask = test_proba >= best["discard_t"]
    y_test_pred[discard_mask] = 1
    # REVIEW cases: use probability >= 0.5 as guess
    y_test_pred[review_mask] = (test_proba[review_mask] >= 0.5).astype(int)
    
    return y_test_pred, test_proba
