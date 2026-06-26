#!/usr/bin/env python3
"""
Experiment v27: Gated Agent v2 expert (mixture-of-experts).

Architecture:
1. Universal model: structured + packet + answer-chain + open-end features
2. Agent evidence model: Agent v2 determinations only (when coverage passes)
3. Gating: weight = min(0.5, agent_coverage_rate) for respondents with agent data
4. For respondents without agent data: p_final = p_universal
5. For respondents with agent data: p_final = (1-weight) * p_universal + weight * p_agent

Agent v2 is only used for Delta and ECHO (the only datasets with meaningful coverage).
For all other datasets, the universal model is used alone.
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
from agent_v2_features import (
    extract_agent_features, get_agent_coverage, get_answer_chain_text, get_question_answer_pairs,
)

warnings.filterwarnings("ignore")


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

    sup_drop = [c for c in X_train.columns if c.startswith("supplier_") or c in ("supplier_x_signal", "supplier_x_signals", "supplier_x_t1", "supplier_x_t2")]
    X_tr_ns = X_train.drop(columns=[c for c in sup_drop if c in X_train.columns], errors='ignore').values
    X_va_ns = X_val.drop(columns=[c for c in sup_drop if c in X_val.columns], errors='ignore').values
    X_te_ns = X_test.drop(columns=[c for c in sup_drop if c in X_test.columns], errors='ignore').values

    # QA TF-IDF
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

    configs = [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.03, "min_samples_leaf": 15},
        {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.08, "min_samples_leaf": 5},
    ]

    # === STAGE 1: Universal model (same sets as v26) ===
    universal_sets = [
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
    universal_sets = [s for s in universal_sets if s is not None]

    baseline_model, baseline_cal, baseline_t, baseline_f1, baseline_acc, baseline_cal_method = \
        train_gbm_calibrated(X_train.values, y_train, X_val.values, y_val, configs[0])

    best_universal = None
    for name, X_tr, X_va, X_te in universal_sets:
        for cfg in configs:
            for cal_method in ["auto", "platt"]:
                model, cal, t, f1, val_acc, cal_used = train_gbm_calibrated(X_tr, y_train, X_va, y_val, cfg, cal_method)
                eligible = val_acc >= (baseline_acc - 0.02)
                score = f1 + 0.3 * (val_acc - baseline_acc)
                if eligible and (best_universal is None or score > best_universal["score"]):
                    best_universal = {"name": name, "model": model, "cal": cal, "threshold": t,
                                      "f1": f1, "val_acc": val_acc, "score": score,
                                      "cal_method": cal_used, "X_tr": X_tr, "X_va": X_va, "X_te": X_te}

    if best_universal is None:
        best_universal = {"model": baseline_model, "cal": baseline_cal, "threshold": baseline_t,
                          "cal_method": baseline_cal_method, "X_tr": X_train.values, "X_va": X_val.values, "X_te": X_test.values}

    # Get universal probabilities
    _, train_proba_uni = predict_calibrated(best_universal["model"], best_universal["cal"], best_universal["threshold"],
                                            best_universal["X_tr"], best_universal["cal_method"])
    _, val_proba_uni = predict_calibrated(best_universal["model"], best_universal["cal"], best_universal["threshold"],
                                          best_universal["X_va"], best_universal["cal_method"])
    _, test_proba_uni = predict_calibrated(best_universal["model"], best_universal["cal"], best_universal["threshold"],
                                           best_universal["X_te"], best_universal["cal_method"])

    # === STAGE 2: Agent expert (if coverage passes) ===
    coverage = get_agent_coverage(dataset_name)
    
    if coverage["has_meaningful_data"]:
        agent_train = extract_agent_features(train_df, dataset_name)
        agent_val = extract_agent_features(val_df, dataset_name)
        agent_test = extract_agent_features(test_df, dataset_name)
        
        # Fill NaN with 0 (coverage indicators preserve the missingness info)
        for af in [agent_train, agent_val, agent_test]:
            for col in af.columns:
                if af[col].isna().any():
                    af[col] = af[col].fillna(0)
        
        # Train agent model
        best_agent = None
        agent_sets = [
            ("agent_only", agent_train.values, agent_val.values, agent_test.values),
            ("agent_uni", np.hstack([agent_train.values, best_universal["X_tr"]]),
             np.hstack([agent_val.values, best_universal["X_va"]]),
             np.hstack([agent_test.values, best_universal["X_te"]])),
        ]
        
        for name, X_tr, X_va, X_te in agent_sets:
            for cfg in configs:
                for cal_method in ["auto", "platt"]:
                    model, cal, t, f1, val_acc, cal_used = train_gbm_calibrated(X_tr, y_train, X_va, y_val, cfg, cal_method)
                    eligible = val_acc >= (baseline_acc - 0.02)
                    score = f1 + 0.3 * (val_acc - baseline_acc)
                    if eligible and (best_agent is None or score > best_agent["score"]):
                        best_agent = {"name": name, "model": model, "cal": cal, "threshold": t,
                                      "f1": f1, "val_acc": val_acc, "score": score,
                                      "cal_method": cal_used, "X_tr": X_tr, "X_va": X_va, "X_te": X_te}
        
        if best_agent is not None:
            # Get agent probabilities
            _, train_proba_agent = predict_calibrated(best_agent["model"], best_agent["cal"], best_agent["threshold"],
                                                      best_agent["X_tr"], best_agent["cal_method"])
            _, val_proba_agent = predict_calibrated(best_agent["model"], best_agent["cal"], best_agent["threshold"],
                                                    best_agent["X_va"], best_agent["cal_method"])
            _, test_proba_agent = predict_calibrated(best_agent["model"], best_agent["cal"], best_agent["threshold"],
                                                     best_agent["X_te"], best_agent["cal_method"])
            
            # Compare universal vs agent vs fusion on validation
            # Try different fusion weights
            best_fusion_f1 = best_universal["f1"]
            best_fusion_t = best_universal["threshold"]
            best_fusion_proba_val = val_proba_uni
            best_fusion_proba_test = test_proba_uni
            best_weight = 0.0
            
            for weight in np.arange(0.1, 0.6, 0.1):
                fused_val = (1 - weight) * val_proba_uni + weight * val_proba_agent
                fused_test = (1 - weight) * test_proba_uni + weight * test_proba_agent
                
                # Find best threshold on fused validation
                best_t = 0.5
                best_f1_t = 0
                for t in np.linspace(0.01, 0.99, 500):
                    pred = (fused_val >= t).astype(int)
                    f1 = f1_score(y_val, pred, zero_division=0)
                    if f1 > best_f1_t:
                        best_f1_t = f1
                        best_t = t
                
                val_acc_fused = accuracy_score(y_val, (fused_val >= best_t).astype(int))
                if best_f1_t > best_fusion_f1 and val_acc_fused >= (baseline_acc - 0.02):
                    best_fusion_f1 = best_f1_t
                    best_fusion_t = best_t
                    best_fusion_proba_val = fused_val
                    best_fusion_proba_test = fused_test
                    best_weight = weight
            
            y_test_pred = (best_fusion_proba_test >= best_fusion_t).astype(int)
            return y_test_pred, best_fusion_proba_test
    
    # No agent coverage or fusion didn't help: use universal model
    y_test_pred = (test_proba_uni >= best_universal["threshold"]).astype(int)
    return y_test_pred, test_proba_uni
