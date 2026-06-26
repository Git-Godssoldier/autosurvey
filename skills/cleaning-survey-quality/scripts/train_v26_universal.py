#!/usr/bin/env python3
"""
Experiment v26: Universal packet backbone.

Establishes the portable baseline using ONLY universally available features:
1. Structured survey features (from Excel extraction)
2. Raw Excel per-question features
3. Staged packet features (supplier, timing, duplicates, answer chain analysis)
4. Answer chain TF-IDF (semantic reconstruction)
5. Question-answer pair TF-IDF (semantic coherence)
6. Open-end text TF-IDF
7. Deep features

NO Agent v2 determinations. This is the universal model that works on
ALL 11 datasets, including those without agent v2 coverage.

Uses proper selection: eligibility constraint + composite score.
Uses Platt scaling for small datasets, isotonic for large ones.
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
from agent_v2_features import (
    get_answer_chain_text, get_question_answer_pairs, load_staged_packets,
)

warnings.filterwarnings("ignore")


def extract_packet_features(df, dataset_name):
    """Extract features from staged packets (available for ALL datasets)."""
    packets = load_staged_packets(dataset_name)
    
    features = pd.DataFrame(index=df.index)
    
    for idx, row in df.iterrows():
        rid = row["respondent_id"]
        pkt = packets.get(rid, {})
        
        # Supplier features
        features.loc[idx, "pkt_supplier_missing"] = 1.0 if pkt.get("supplier_missing", True) else 0.0
        features.loc[idx, "pkt_supplier_reject_rate"] = float(pkt.get("supplier_reject_rate", 0))
        
        # Timing features (contextualized)
        qtime_sec = float(pkt.get("qtime_seconds", 0))
        features.loc[idx, "pkt_qtime_seconds"] = qtime_sec
        features.loc[idx, "pkt_qtime_minutes"] = float(pkt.get("qtime_minutes", 0))
        tp = pkt.get("timing_percentile", "")
        features.loc[idx, "pkt_timing_bottom_10"] = 1.0 if "bottom_10" in tp else 0.0
        features.loc[idx, "pkt_timing_bottom_25"] = 1.0 if "bottom_25" in tp or "bottom_10" in tp else 0.0
        features.loc[idx, "pkt_timing_below_median"] = 1.0 if "below_median" in tp or "bottom" in tp else 0.0
        
        # Duplicate memberships
        dups = pkt.get("duplicate_memberships", [])
        features.loc[idx, "pkt_dup_count"] = float(len(dups))
        features.loc[idx, "pkt_has_dup"] = 1.0 if len(dups) > 0 else 0.0
        if dups:
            max_shared = max(d.get("shared_with_count", 0) for d in dups)
            features.loc[idx, "pkt_max_dup_shared"] = float(max_shared)
            dup_fields = [d.get("field", "") for d in dups]
            features.loc[idx, "pkt_dup_ua"] = 1.0 if "userAgent" in dup_fields else 0.0
            features.loc[idx, "pkt_dup_oe"] = 1.0 if any("open" in f.lower() or "text" in f.lower() for f in dup_fields) else 0.0
        else:
            features.loc[idx, "pkt_max_dup_shared"] = 0.0
            features.loc[idx, "pkt_dup_ua"] = 0.0
            features.loc[idx, "pkt_dup_oe"] = 0.0
        
        # Client quality signals
        signals = pkt.get("client_quality_signals", [])
        features.loc[idx, "pkt_signal_count"] = float(pkt.get("client_signal_count", len(signals)))
        
        # Answer chain analysis
        chain = pkt.get("answer_chain", [])
        features.loc[idx, "pkt_answer_count"] = float(pkt.get("answer_count", len(chain)))
        
        if chain:
            types = [a.get("answer_type", "") for a in chain]
            features.loc[idx, "pkt_coded_count"] = float(types.count("coded"))
            features.loc[idx, "pkt_oe_count"] = float(types.count("open_end"))
            features.loc[idx, "pkt_matrix_count"] = float(types.count("matrix_cell"))
            
            # Time per question (contextualized timing)
            total_q = len(chain)
            features.loc[idx, "pkt_time_per_q"] = qtime_sec / (total_q + 1)
            features.loc[idx, "pkt_time_per_q_log"] = np.log1p(qtime_sec / (total_q + 1))
            
            # Open-end text from chain
            oe_texts = [str(a.get("label", "") or a.get("raw_value", "")) for a in chain if a.get("answer_type") == "open_end"]
            oe_text = " ".join(oe_texts)
            features.loc[idx, "pkt_oe_text_len"] = float(len(oe_text))
            features.loc[idx, "pkt_oe_word_count"] = float(len(oe_text.split()))
            
            # Coded answer diversity
            coded = [str(a.get("label", "") or a.get("raw_value", "")) for a in chain if a.get("answer_type") == "coded"]
            if coded:
                features.loc[idx, "pkt_coded_unique_ratio"] = len(set(coded)) / len(coded)
                from collections import Counter
                features.loc[idx, "pkt_coded_most_common_freq"] = Counter(coded).most_common(1)[0][1] / len(coded)
            else:
                features.loc[idx, "pkt_coded_unique_ratio"] = 1.0
                features.loc[idx, "pkt_coded_most_common_freq"] = 0.0
            
            # Matrix answer patterns
            matrix = [str(a.get("label", "") or a.get("raw_value", "")) for a in chain if a.get("answer_type") == "matrix_cell"]
            if matrix:
                ur = len(set(matrix)) / len(matrix)
                features.loc[idx, "pkt_matrix_unique_ratio"] = ur
                features.loc[idx, "pkt_matrix_straightline"] = 1.0 if ur <= 0.2 and len(matrix) >= 5 else 0.0
                features.loc[idx, "pkt_matrix_near_straightline"] = 1.0 if ur <= 0.4 and len(matrix) >= 5 else 0.0
                # Longest identical run
                longest_run = 1
                current_run = 1
                for i in range(1, len(matrix)):
                    if matrix[i] == matrix[i-1]:
                        current_run += 1
                        longest_run = max(longest_run, current_run)
                    else:
                        current_run = 1
                features.loc[idx, "pkt_matrix_longest_run"] = float(longest_run)
                features.loc[idx, "pkt_matrix_longest_run_ratio"] = longest_run / len(matrix)
            else:
                features.loc[idx, "pkt_matrix_unique_ratio"] = 1.0
                features.loc[idx, "pkt_matrix_straightline"] = 0.0
                features.loc[idx, "pkt_matrix_near_straightline"] = 0.0
                features.loc[idx, "pkt_matrix_longest_run"] = 0.0
                features.loc[idx, "pkt_matrix_longest_run_ratio"] = 0.0
        else:
            for col in ["pkt_coded_count", "pkt_oe_count", "pkt_matrix_count",
                        "pkt_time_per_q", "pkt_time_per_q_log",
                        "pkt_oe_text_len", "pkt_oe_word_count",
                        "pkt_matrix_longest_run", "pkt_matrix_longest_run_ratio"]:
                features.loc[idx, col] = 0.0
            features.loc[idx, "pkt_coded_unique_ratio"] = 1.0
            features.loc[idx, "pkt_coded_most_common_freq"] = 0.0
            features.loc[idx, "pkt_matrix_unique_ratio"] = 1.0
            features.loc[idx, "pkt_matrix_straightline"] = 0.0
            features.loc[idx, "pkt_matrix_near_straightline"] = 0.0
    
    return features.fillna(0)


def train_gbm_calibrated(X_train, y_train, X_val, y_val, cfg, calibration="auto"):
    """Train GBM with separate calibration and threshold selection."""
    n_pos = max((y_train == 1).sum(), 1)
    n_neg = max((y_train == 0).sum(), 1)
    w = np.where(y_train == 1, len(y_train) / (2 * n_pos), len(y_train) / (2 * n_neg))
    
    model = GradientBoostingClassifier(**cfg, subsample=0.8, random_state=42)
    model.fit(X_train, y_train, sample_weight=w)
    
    y_train_proba = model.predict_proba(X_train)[:, 1]
    
    n_train = len(y_train)
    if calibration == "auto":
        calibration = "isotonic" if n_train >= 200 else "platt"
    
    if calibration == "isotonic":
        cal = IsotonicRegression(out_of_bounds='clip')
        cal.fit(y_train_proba, y_train)
        y_val_cal = cal.transform(model.predict_proba(X_val)[:, 1])
    else:
        cal = LogisticRegression(C=1.0)
        cal.fit(y_train_proba.reshape(-1, 1), y_train)
        y_val_cal = cal.predict_proba(model.predict_proba(X_val)[:, 1].reshape(-1, 1))[:, 1]
    
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
    proba = model.predict_proba(X)[:, 1]
    if calibration == "isotonic":
        cal_proba = cal.transform(proba)
    else:
        cal_proba = cal.predict_proba(proba.reshape(-1, 1))[:, 1]
    return (cal_proba >= threshold).astype(int), cal_proba


def train_and_predict(train_df, val_df, test_df):
    dataset_name = train_df["dataset"].iloc[0] if "dataset" in train_df.columns else ""
    
    train_df = train_df.copy()
    val_df = val_df.copy()
    test_df = test_df.copy()

    train_text = train_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in train_df.columns else [""] * len(train_df)
    val_text = val_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in val_df.columns else [""] * len(val_df)
    test_text = test_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in test_df.columns else [""] * len(test_df)

    # Answer chain text (semantic reconstruction)
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

    # Packet features (universal)
    pkt_train = extract_packet_features(train_df, dataset_name)
    pkt_val = extract_packet_features(val_df, dataset_name)
    pkt_test = extract_packet_features(test_df, dataset_name)

    # Deep features
    deep_train = extract_deep_features(train_df)
    deep_val = extract_deep_features(val_df)
    deep_test = extract_deep_features(test_df)

    # TF-IDF on open-end text
    tfidf_oe = get_tfidf_features(train_text, val_text, test_text, word=True, char=True)

    # TF-IDF on answer chain
    chain_svd_train = chain_svd_val = chain_svd_test = None
    try:
        chain_tfidf = TfidfVectorizer(max_features=200, ngram_range=(1, 1), min_df=2, max_df=0.9, sublinear_tf=True)
        chain_tfidf.fit(chain_train)
        ct, cv, cte = chain_tfidf.transform(chain_train), chain_tfidf.transform(chain_val), chain_tfidf.transform(chain_test)
        n = min(40, ct.shape[1], ct.shape[0] - 1)
        svd = TruncatedSVD(n_components=n, random_state=42)
        chain_svd_train = svd.fit_transform(ct)
        chain_svd_val = svd.transform(cv)
        chain_svd_test = svd.transform(cte)
    except Exception:
        pass

    # TF-IDF on question-answer pairs
    qa_svd_train = qa_svd_val = qa_svd_test = None
    try:
        qa_tfidf = TfidfVectorizer(max_features=200, ngram_range=(1, 2), min_df=2, max_df=0.9,
                                    stop_words='english', sublinear_tf=True)
        qa_tfidf.fit(qa_train)
        qt, qv, qte = qa_tfidf.transform(qa_train), qa_tfidf.transform(qa_val), qa_tfidf.transform(qa_test)
        n = min(40, qt.shape[1], qt.shape[0] - 1)
        svd = TruncatedSVD(n_components=n, random_state=42)
        qa_svd_train = svd.fit_transform(qt)
        qa_svd_val = svd.transform(qv)
        qa_svd_test = svd.transform(qte)
    except Exception:
        pass

    # Supplier risk columns
    sup_drop = [c for c in X_train.columns if c.startswith("supplier_") or 
                c in ("supplier_x_signal", "supplier_x_signals", "supplier_x_t1", "supplier_x_t2")]
    X_tr_ns = X_train.drop(columns=[c for c in sup_drop if c in X_train.columns], errors='ignore').values
    X_va_ns = X_val.drop(columns=[c for c in sup_drop if c in X_val.columns], errors='ignore').values
    X_te_ns = X_test.drop(columns=[c for c in sup_drop if c in X_test.columns], errors='ignore').values

    # Define extra arrays
    oe_arr = (tfidf_oe[0], tfidf_oe[1], tfidf_oe[2]) if tfidf_oe[0] is not None else (None, None, None)
    pkt_arr = (pkt_train.values, pkt_val.values, pkt_test.values)
    chain_arr = (chain_svd_train, chain_svd_val, chain_svd_test) if chain_svd_train is not None else (None, None, None)
    qa_arr = (qa_svd_train, qa_svd_val, qa_svd_test) if qa_svd_train is not None else (None, None, None)
    deep_arr = (deep_train.values, deep_val.values, deep_test.values)

    # Build feature sets
    feature_sets = []
    
    def make_set(name, extra_arrays, base="sup"):
        bt, bv, bte = (X_train.values, X_val.values, X_test.values) if base == "sup" else (X_tr_ns, X_va_ns, X_te_ns)
        parts_t, parts_v, parts_te = [bt], [bv], [bte]
        for a in extra_arrays:
            if a[0] is not None:
                parts_t.append(a[0]); parts_v.append(a[1]); parts_te.append(a[2])
        return (name, np.hstack(parts_t), np.hstack(parts_v), np.hstack(parts_te))

    # Universal backbone combinations
    feature_sets.append(make_set("struct", []))
    feature_sets.append(make_set("pkt", [pkt_arr]))
    feature_sets.append(make_set("oe", [oe_arr]))
    feature_sets.append(make_set("oe_pkt", [oe_arr, pkt_arr]))
    feature_sets.append(make_set("oe_pkt_deep", [oe_arr, pkt_arr, deep_arr]))
    feature_sets.append(make_set("oe_pkt_chain", [oe_arr, pkt_arr, chain_arr]))
    feature_sets.append(make_set("oe_pkt_qa", [oe_arr, pkt_arr, qa_arr]))
    feature_sets.append(make_set("all", [oe_arr, pkt_arr, chain_arr, qa_arr, deep_arr]))
    
    # Without supplier
    feature_sets.append(make_set("no_sup", [], "no_sup"))
    feature_sets.append(make_set("no_sup_pkt", [pkt_arr], "no_sup"))
    feature_sets.append(make_set("no_sup_oe_pkt", [oe_arr, pkt_arr], "no_sup"))
    feature_sets.append(make_set("no_sup_all", [oe_arr, pkt_arr, chain_arr, qa_arr, deep_arr], "no_sup"))

    configs = [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.03, "min_samples_leaf": 15},
        {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.08, "min_samples_leaf": 5},
    ]

    # Baseline
    baseline_model, baseline_cal, baseline_t, baseline_f1, baseline_acc, baseline_cal_method = \
        train_gbm_calibrated(X_train.values, y_train, X_val.values, y_val, configs[0])

    approaches = []
    for name, X_tr, X_va, X_te in feature_sets:
        for cfg in configs:
            for cal_method in ["auto", "platt"]:
                model, cal, t, f1, val_acc, cal_used = train_gbm_calibrated(
                    X_tr, y_train, X_va, y_val, cfg, cal_method)
                eligible = val_acc >= (baseline_acc - 0.02)  # 2% tolerance
                score = f1 + 0.3 * (val_acc - baseline_acc)
                approaches.append({
                    "name": name, "model": model, "cal": cal, "threshold": t,
                    "f1": f1, "val_acc": val_acc, "score": score,
                    "eligible": eligible, "cal_method": cal_used, "X_te": X_te,
                })

    eligible_approaches = [a for a in approaches if a["eligible"]]
    if not eligible_approaches:
        best = {"model": baseline_model, "cal": baseline_cal, "threshold": baseline_t,
                "cal_method": baseline_cal_method, "X_te": X_test.values}
    else:
        best = max(eligible_approaches, key=lambda a: a["score"])

    y_test_cal_proba = predict_calibrated(
        best["model"], best["cal"], best["threshold"], best["X_te"], best["cal_method"])[1]
    y_test_pred = (y_test_cal_proba >= best["threshold"]).astype(int)
    return y_test_pred, y_test_cal_proba
