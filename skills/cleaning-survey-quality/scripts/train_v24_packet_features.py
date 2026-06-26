#!/usr/bin/env python3
"""
Experiment 24: Staged packet features + semantic reconstruction for ALL datasets.

The agent v2 determinations are only available for Delta and ECHO.
But the staged packets (with answer chains) are available for ALL 11 datasets.

This script uses:
1. Structured features (from Excel extraction)
2. Raw Excel per-question features
3. Staged packet features (supplier, timing, duplicates, answer chain analysis)
4. Answer chain TF-IDF (semantic reconstruction - available for ALL datasets)
5. Open-end text TF-IDF
6. Deep features
7. Per-dataset model selection with accuracy filter

The agent v2 determinations are only added for Delta and ECHO (where they exist).
"""
from __future__ import annotations
import warnings, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score, accuracy_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from survey_quality_ml import prepare_features
from train_v13_deep import extract_deep_features
from train_v14_per_dataset_best import get_tfidf_features, train_gbm
from train_v15_raw_excel import extract_raw_excel_features
from agent_v2_features import (
    extract_agent_features, get_agent_justification_text, get_answer_chain_text,
    load_agent_determinations, load_staged_packets,
)

warnings.filterwarnings("ignore")


def extract_packet_features(df, dataset_name):
    """Extract features from staged packets (available for ALL datasets)."""
    packets = load_staged_packets(dataset_name)
    
    features = pd.DataFrame(index=df.index)
    
    for idx, row in df.iterrows():
        rid = row["respondent_id"]
        pkt = packets.get(rid, {})
        
        # Supplier features from packet
        features.loc[idx, "pkt_supplier_missing"] = 1 if pkt.get("supplier_missing", True) else 0
        features.loc[idx, "pkt_supplier_reject_rate"] = pkt.get("supplier_reject_rate", 0)
        
        # Timing from packet
        features.loc[idx, "pkt_qtime_seconds"] = pkt.get("qtime_seconds", 0)
        features.loc[idx, "pkt_qtime_minutes"] = pkt.get("qtime_minutes", 0)
        tp = pkt.get("timing_percentile", "")
        features.loc[idx, "pkt_timing_bottom_10"] = 1 if "bottom_10" in tp else 0
        features.loc[idx, "pkt_timing_bottom_25"] = 1 if "bottom_25" in tp or "bottom_10" in tp else 0
        features.loc[idx, "pkt_timing_below_median"] = 1 if "below_median" in tp or "bottom" in tp else 0
        features.loc[idx, "pkt_timing_above_median"] = 1 if "above_median" in tp or "top" in tp else 0
        
        # Duplicate memberships
        dups = pkt.get("duplicate_memberships", [])
        features.loc[idx, "pkt_dup_count"] = len(dups)
        features.loc[idx, "pkt_has_dup"] = 1 if len(dups) > 0 else 0
        if dups:
            max_shared = max(d.get("shared_with_count", 0) for d in dups)
            features.loc[idx, "pkt_max_dup_shared"] = max_shared
            # Count duplicate types
            dup_fields = [d.get("field", "") for d in dups]
            features.loc[idx, "pkt_dup_ip"] = 1 if "ip" in dup_fields else 0
            features.loc[idx, "pkt_dup_ua"] = 1 if "userAgent" in dup_fields else 0
            features.loc[idx, "pkt_dup_oe"] = 1 if any("open" in f.lower() or "text" in f.lower() for f in dup_fields) else 0
        else:
            features.loc[idx, "pkt_max_dup_shared"] = 0
            features.loc[idx, "pkt_dup_ip"] = 0
            features.loc[idx, "pkt_dup_ua"] = 0
            features.loc[idx, "pkt_dup_oe"] = 0
        
        # Client quality signals from packet
        signals = pkt.get("client_quality_signals", [])
        features.loc[idx, "pkt_signal_count"] = pkt.get("client_signal_count", len(signals))
        
        # Answer chain analysis
        chain = pkt.get("answer_chain", [])
        features.loc[idx, "pkt_answer_count"] = pkt.get("answer_count", len(chain))
        
        if chain:
            # Answer type distribution
            types = [a.get("answer_type", "") for a in chain]
            features.loc[idx, "pkt_coded_count"] = types.count("coded")
            features.loc[idx, "pkt_oe_count"] = types.count("open_end")
            features.loc[idx, "pkt_matrix_count"] = types.count("matrix_cell")
            features.loc[idx, "pkt_demo_count"] = types.count("demographic")
            
            # Open-end text from chain
            oe_texts = [str(a.get("label", "") or a.get("raw_value", "")) for a in chain if a.get("answer_type") == "open_end"]
            oe_text = " ".join(oe_texts)
            features.loc[idx, "pkt_oe_text_len"] = len(oe_text)
            features.loc[idx, "pkt_oe_word_count"] = len(oe_text.split())
            features.loc[idx, "pkt_oe_avg_word_len"] = np.mean([len(w) for w in oe_text.split()]) if oe_text.split() else 0
            
            # Coded answer diversity
            coded = [str(a.get("label", "") or a.get("raw_value", "")) for a in chain if a.get("answer_type") == "coded"]
            if coded:
                features.loc[idx, "pkt_coded_unique_ratio"] = len(set(coded)) / len(coded)
                from collections import Counter
                features.loc[idx, "pkt_coded_most_common_freq"] = Counter(coded).most_common(1)[0][1] / len(coded)
            else:
                features.loc[idx, "pkt_coded_unique_ratio"] = 1.0
                features.loc[idx, "pkt_coded_most_common_freq"] = 0
            
            # Matrix answer diversity
            matrix = [str(a.get("label", "") or a.get("raw_value", "")) for a in chain if a.get("answer_type") == "matrix_cell"]
            if matrix:
                features.loc[idx, "pkt_matrix_unique_ratio"] = len(set(matrix)) / len(matrix)
                features.loc[idx, "pkt_matrix_straightline"] = 1 if len(set(matrix)) / len(matrix) <= 0.2 and len(matrix) >= 5 else 0
                features.loc[idx, "pkt_matrix_near_straightline"] = 1 if len(set(matrix)) / len(matrix) <= 0.4 and len(matrix) >= 5 else 0
            else:
                features.loc[idx, "pkt_matrix_unique_ratio"] = 1.0
                features.loc[idx, "pkt_matrix_straightline"] = 0
                features.loc[idx, "pkt_matrix_near_straightline"] = 0
            
            # Question text analysis (semantic context)
            qtexts = [str(a.get("question_text", "")) for a in chain if a.get("question_text")]
            features.loc[idx, "pkt_qtext_total_len"] = sum(len(q) for q in qtexts)
            features.loc[idx, "pkt_qtext_count"] = len(qtexts)
            
            # Answer-label vs raw-value mismatch (label is human-readable, raw is numeric)
            mismatches = sum(1 for a in chain if a.get("label") and a.get("raw_value") and str(a.get("label")) != str(a.get("raw_value")))
            features.loc[idx, "pkt_labeled_ratio"] = mismatches / len(chain) if chain else 0
        else:
            for col in ["pkt_coded_count", "pkt_oe_count", "pkt_matrix_count", "pkt_demo_count",
                        "pkt_oe_text_len", "pkt_oe_word_count", "pkt_oe_avg_word_len",
                        "pkt_qtext_total_len", "pkt_qtext_count", "pkt_labeled_ratio"]:
                features.loc[idx, col] = 0
            features.loc[idx, "pkt_coded_unique_ratio"] = 1.0
            features.loc[idx, "pkt_coded_most_common_freq"] = 0
            features.loc[idx, "pkt_matrix_unique_ratio"] = 1.0
            features.loc[idx, "pkt_matrix_straightline"] = 0
            features.loc[idx, "pkt_matrix_near_straightline"] = 0
    
    return features.fillna(0)


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

    # Packet features (available for ALL datasets)
    pkt_train = extract_packet_features(train_df, dataset_name)
    pkt_val = extract_packet_features(val_df, dataset_name)
    pkt_test = extract_packet_features(test_df, dataset_name)

    # Agent v2 determination features (only for Delta and ECHO)
    dets = load_agent_determinations(dataset_name)
    has_agent_dets = any(d.get("decision") in ("DISCARD", "REVIEW") for d in dets.values())
    
    agent_train = None
    agent_val = None
    agent_test = None
    if has_agent_dets:
        agent_train = extract_agent_features(train_df, dataset_name).fillna(0)
        agent_val = extract_agent_features(val_df, dataset_name).fillna(0)
        agent_test = extract_agent_features(test_df, dataset_name).fillna(0)

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
    deep_arr = (deep_train.values, deep_val.values, deep_test.values)
    agent_arr = (agent_train.values, agent_val.values, agent_test.values) if agent_train is not None else (None, None, None)

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

    # v19 base sets
    feature_sets.append(make_set("struct", []))
    feature_sets.append(make_set("oe", [oe_arr]))
    feature_sets.append(make_set("oe_deep", [oe_arr, deep_arr]))
    feature_sets.append(make_set("no_sup", [], "no_sup"))
    feature_sets.append(make_set("no_sup_oe", [oe_arr], "no_sup"))
    feature_sets.append(make_set("no_sup_oe_deep", [oe_arr, deep_arr], "no_sup"))
    
    # Packet features (available for all)
    feature_sets.append(make_set("pkt", [pkt_arr]))
    feature_sets.append(make_set("oe_pkt", [oe_arr, pkt_arr]))
    feature_sets.append(make_set("oe_pkt_chain", [oe_arr, pkt_arr, chain_arr]))
    feature_sets.append(make_set("oe_pkt_deep", [oe_arr, pkt_arr, deep_arr]))
    feature_sets.append(make_set("all_pkt", [oe_arr, pkt_arr, chain_arr, deep_arr]))
    feature_sets.append(make_set("no_sup_pkt", [pkt_arr], "no_sup"))
    feature_sets.append(make_set("no_sup_oe_pkt", [oe_arr, pkt_arr], "no_sup"))
    feature_sets.append(make_set("no_sup_all_pkt", [oe_arr, pkt_arr, chain_arr, deep_arr], "no_sup"))
    
    # Agent determination features (only for Delta and ECHO)
    if agent_arr[0] is not None:
        feature_sets.append(make_set("agent", [agent_arr]))
        feature_sets.append(make_set("oe_pkt_agent", [oe_arr, pkt_arr, agent_arr]))
        feature_sets.append(make_set("all_agent", [oe_arr, pkt_arr, chain_arr, deep_arr, agent_arr]))
        feature_sets.append(make_set("no_sup_agent", [agent_arr], "no_sup"))
        feature_sets.append(make_set("no_sup_all_agent", [oe_arr, pkt_arr, chain_arr, deep_arr, agent_arr], "no_sup"))

    configs = [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.03, "min_samples_leaf": 15},
        {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.08, "min_samples_leaf": 5},
    ]

    # Baseline
    baseline_m, baseline_iso, baseline_t, baseline_f1 = train_gbm(
        X_train.values, y_train, X_val.values, y_val, configs[0])

    approaches = []
    for name, X_tr, X_va, X_te in feature_sets:
        for cfg in configs:
            m, iso, t, f1 = train_gbm(X_tr, y_train, X_va, y_val, cfg)
            y_val_pred = (iso.transform(m.predict_proba(X_va)[:, 1]) >= t).astype(int)
            val_acc = accuracy_score(y_val, y_val_pred)
            y_val_base = (baseline_iso.transform(baseline_m.predict_proba(X_val.values)[:, 1]) >= baseline_t).astype(int)
            base_acc = accuracy_score(y_val, y_val_base)
            score = f1 + 0.3 * (val_acc - base_acc)
            approaches.append((name, m, iso, t, f1, score, X_tr, X_va, X_te))

    best = max(approaches, key=lambda a: a[4])
    name, model, iso, best_t, best_f1, _, _, _, X_te = best

    y_test_cal = iso.transform(model.predict_proba(X_te)[:, 1])
    y_test_pred = (y_test_cal >= best_t).astype(int)
    return y_test_pred, y_test_cal
