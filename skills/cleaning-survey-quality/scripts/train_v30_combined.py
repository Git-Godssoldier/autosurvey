#!/usr/bin/env python3
"""
Experiment v30: v26 universal backbone + v19 simple selection + selective option.

Combines the best of all approaches:
1. v26's universal packet backbone (structured + packet + chain + QA + deep)
2. v19's simple F1 threshold selection (no review penalty)
3. v29's selective classifier as an ADDITIONAL option (not replacement)

The per-dataset selection tries both simple threshold and selective threshold,
and picks whichever has better validation F1.
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
sys.path.insert(0, str(Path(__file__).parent))
from survey_quality_ml import prepare_features
from train_v13_deep import extract_deep_features
from train_v14_per_dataset_best import get_tfidf_features
from train_v15_raw_excel import extract_raw_excel_features
from train_v26_universal import extract_packet_features, train_gbm_calibrated, predict_calibrated
from agent_v2_features import get_answer_chain_text, get_question_answer_pairs

warnings.filterwarnings("ignore")


def optimize_simple_threshold(y_val, val_proba):
    """Simple F1-optimal threshold (v19 approach)."""
    best_f1, best_t = 0, 0.5
    for t in np.linspace(0.01, 0.99, 500):
        pred = (val_proba >= t).astype(int)
        f1 = f1_score(y_val, pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = t
    return best_t, best_f1


def optimize_selective_thresholds(y_val, val_proba, baseline_acc, review_penalty=0.05):
    """Selective thresholds with low review penalty."""
    best_score = -1
    best_dt = 0.5
    best_kt = 0.0
    best_f1 = 0
    
    for dt in np.linspace(0.3, 0.95, 40):
        for kt in np.linspace(0.0, 0.5, 20):
            if kt >= dt:
                continue
            pred = np.zeros(len(y_val))
            review_mask = (val_proba > kt) & (val_proba < dt)
            discard_mask = val_proba >= dt
            pred[discard_mask] = 1
            pred[review_mask] = (val_proba[review_mask] >= 0.5).astype(int)
            f1 = f1_score(y_val, pred, zero_division=0)
            acc = accuracy_score(y_val, pred)
            review_rate = review_mask.mean()
            if acc < baseline_acc - 0.02:
                continue
            score = f1 - review_penalty * review_rate
            if score > best_score:
                best_score = score
                best_dt = dt
                best_kt = kt
                best_f1 = f1
    return best_dt, best_kt, best_f1


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
                _, val_proba = predict_calibrated(model, cal, 0.5, X_va, cal_used)
                
                # Option 1: Simple F1 threshold (v19 style)
                simple_t, simple_f1 = optimize_simple_threshold(y_val, val_proba)
                simple_pred = (val_proba >= simple_t).astype(int)
                simple_acc = accuracy_score(y_val, simple_pred)
                simple_eligible = simple_acc >= (baseline_acc - 0.02)
                simple_score = simple_f1 + 0.3 * (simple_acc - baseline_acc)
                if simple_eligible:
                    approaches.append({
                        "name": f"{name}_simple", "model": model, "cal": cal,
                        "threshold": simple_t, "keep_t": 0.0, "selective": False,
                        "f1": simple_f1, "val_acc": simple_acc, "score": simple_score,
                        "cal_method": cal_used, "X_te": X_te,
                    })
                
                # Option 2: Selective thresholds (v29 style, low penalty)
                sel_dt, sel_kt, sel_f1 = optimize_selective_thresholds(
                    y_val, val_proba, baseline_acc, review_penalty=0.05)
                sel_pred = np.zeros(len(y_val))
                review_mask = (val_proba > sel_kt) & (val_proba < sel_dt)
                sel_pred[val_proba >= sel_dt] = 1
                sel_pred[review_mask] = (val_proba[review_mask] >= 0.5).astype(int)
                sel_acc = accuracy_score(y_val, sel_pred)
                sel_eligible = sel_acc >= (baseline_acc - 0.02)
                sel_score = sel_f1 + 0.3 * (sel_acc - baseline_acc)
                if sel_eligible and sel_f1 > 0:
                    approaches.append({
                        "name": f"{name}_selective", "model": model, "cal": cal,
                        "threshold": sel_dt, "keep_t": sel_kt, "selective": True,
                        "f1": sel_f1, "val_acc": sel_acc, "score": sel_score,
                        "cal_method": cal_used, "X_te": X_te,
                    })

    if not approaches:
        _, test_proba = predict_calibrated(baseline_model, baseline_cal, 0.5, X_test.values, baseline_cal_method)
        return (test_proba >= baseline_t).astype(int), test_proba

    best = max(approaches, key=lambda a: a["score"])
    
    _, test_proba = predict_calibrated(best["model"], best["cal"], 0.5, best["X_te"], best["cal_method"])
    
    if best["selective"]:
        y_test_pred = np.zeros(len(test_proba))
        review_mask = (test_proba > best["keep_t"]) & (test_proba < best["threshold"])
        y_test_pred[test_proba >= best["threshold"]] = 1
        y_test_pred[review_mask] = (test_proba[review_mask] >= 0.5).astype(int)
    else:
        y_test_pred = (test_proba >= best["threshold"]).astype(int)
    
    return y_test_pred, test_proba
