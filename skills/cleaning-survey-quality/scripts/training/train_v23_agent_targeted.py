#!/usr/bin/env python3
"""
Experiment 23: v19 base + agent v2 as targeted option.

Uses v19's exact approach (8 feature sets x 3 configs with accuracy filter)
but adds agent v2 features as ONE additional extra option, not 15.

Feature sets:
1-8: v19's original sets (struct, +oe, +agent, +oe_agent, +just, +chain, etc.)
  But only the most useful combinations, not all 15.

The key insight from v20: agent features boost TFG Q1 to 93% F1.
The key insight from v19: per-dataset selection with accuracy filter is best.
Combine: let per-dataset selection choose whether to add agent features.
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
sys.path.insert(0, str(Path(__file__).parent.parent))
from survey_quality_ml import prepare_features
from train_v13_deep import extract_deep_features
from train_v14_per_dataset_best import get_tfidf_features, train_gbm
from train_v15_raw_excel import extract_raw_excel_features
from agent_v2_features import extract_agent_features, get_agent_justification_text, get_answer_chain_text

warnings.filterwarnings("ignore")


def train_and_predict(train_df, val_df, test_df):
    dataset_name = train_df["dataset"].iloc[0] if "dataset" in train_df.columns else ""
    
    train_df = train_df.copy()
    val_df = val_df.copy()
    test_df = test_df.copy()

    train_text = train_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in train_df.columns else [""] * len(train_df)
    val_text = val_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in val_df.columns else [""] * len(val_df)
    test_text = test_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in test_df.columns else [""] * len(test_df)

    # Agent justification text
    agent_just_train = get_agent_justification_text(train_df, dataset_name)
    agent_just_val = get_agent_justification_text(val_df, dataset_name)
    agent_just_test = get_agent_justification_text(test_df, dataset_name)

    # Answer chain text (semantic reconstruction)
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

    # Agent v2 features (separate matrix)
    agent_train = extract_agent_features(train_df, dataset_name).fillna(0)
    agent_val = extract_agent_features(val_df, dataset_name).fillna(0)
    agent_test = extract_agent_features(test_df, dataset_name).fillna(0)

    # Deep features
    deep_train = extract_deep_features(train_df)
    deep_val = extract_deep_features(val_df)
    deep_test = extract_deep_features(test_df)

    # TF-IDF on open-end text
    tfidf_oe = get_tfidf_features(train_text, val_text, test_text, word=True, char=True)

    # TF-IDF on agent justification text
    just_svd_train = just_svd_val = just_svd_test = None
    try:
        just_tfidf = TfidfVectorizer(max_features=100, ngram_range=(1, 2), min_df=2, max_df=0.9,
                                      stop_words='english', sublinear_tf=True)
        just_tfidf.fit(agent_just_train)
        jt = just_tfidf.transform(agent_just_train)
        jv = just_tfidf.transform(agent_just_val)
        jte = just_tfidf.transform(agent_just_test)
        n = min(25, jt.shape[1], jt.shape[0] - 1)
        svd = TruncatedSVD(n_components=n, random_state=42)
        just_svd_train = svd.fit_transform(jt)
        just_svd_val = svd.transform(jv)
        just_svd_test = svd.transform(jte)
    except Exception:
        pass

    # TF-IDF on answer chain (semantic reconstruction)
    chain_svd_train = chain_svd_val = chain_svd_test = None
    try:
        chain_tfidf = TfidfVectorizer(max_features=150, ngram_range=(1, 1), min_df=2, max_df=0.9,
                                       sublinear_tf=True)
        chain_tfidf.fit(chain_train)
        ct = chain_tfidf.transform(chain_train)
        cv = chain_tfidf.transform(chain_val)
        cte = chain_tfidf.transform(chain_test)
        n = min(30, ct.shape[1], ct.shape[0] - 1)
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

    # Build feature sets - focused, not too many
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

    oe_arr = (tfidf_oe[0], tfidf_oe[1], tfidf_oe[2]) if tfidf_oe[0] is not None else (None, None, None)
    agent_arr = (agent_train.values, agent_val.values, agent_test.values)
    just_arr = (just_svd_train, just_svd_val, just_svd_test) if just_svd_train is not None else (None, None, None)
    chain_arr = (chain_svd_train, chain_svd_val, chain_svd_test) if chain_svd_train is not None else (None, None, None)
    deep_arr = (deep_train.values, deep_val.values, deep_test.values)

    # v19 original sets (with supplier)
    feature_sets.append(make_set("struct", []))
    feature_sets.append(make_set("oe", [oe_arr]))
    feature_sets.append(make_set("oe_deep", [oe_arr, deep_arr]))
    
    # v19 original sets (without supplier)
    feature_sets.append(make_set("no_sup", [], "no_sup"))
    feature_sets.append(make_set("no_sup_oe", [oe_arr], "no_sup"))
    feature_sets.append(make_set("no_sup_oe_deep", [oe_arr, deep_arr], "no_sup"))
    
    # NEW: Agent v2 sets (the key addition)
    feature_sets.append(make_set("agent", [agent_arr]))
    feature_sets.append(make_set("oe_agent", [oe_arr, agent_arr]))
    feature_sets.append(make_set("oe_agent_just", [oe_arr, agent_arr, just_arr]))
    feature_sets.append(make_set("oe_agent_chain", [oe_arr, agent_arr, chain_arr]))
    feature_sets.append(make_set("oe_agent_just_chain", [oe_arr, agent_arr, just_arr, chain_arr]))
    feature_sets.append(make_set("all", [oe_arr, agent_arr, just_arr, chain_arr, deep_arr]))
    
    # NEW: Agent without supplier
    feature_sets.append(make_set("no_sup_agent", [agent_arr], "no_sup"))
    feature_sets.append(make_set("no_sup_oe_agent", [oe_arr, agent_arr], "no_sup"))
    feature_sets.append(make_set("no_sup_all", [oe_arr, agent_arr, just_arr, chain_arr, deep_arr], "no_sup"))

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
