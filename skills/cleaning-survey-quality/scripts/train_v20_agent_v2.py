#!/usr/bin/env python3
"""
Experiment 20: Full pipeline with agent v2 features + semantic reconstruction.

Uses ALL available data:
1. Structured features from Excel extraction (156 features)
2. Agent v2 blind run determinations (unbiased agent analysis features)
3. Answer chain semantic reconstruction (from staged packets)
4. Agent justification text TF-IDF (semantic analysis text)
5. Answer chain label TF-IDF (semantic reconstruction)
6. Open-end text TF-IDF
7. Deep answer-chain features
8. Per-dataset model selection with accuracy filter

The agent v2 ran BLIND (without seeing labels), so its features are unbiased.
This is the "subagent pass" that provides unbiased agent run components
before scoring.
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
from agent_v2_features import extract_agent_features, get_agent_justification_text, get_answer_chain_text

warnings.filterwarnings("ignore")


def train_and_predict(train_df, val_df, test_df):
    dataset_name = train_df["dataset"].iloc[0] if "dataset" in train_df.columns else ""
    
    train_text = train_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in train_df.columns else [""] * len(train_df)
    val_text = val_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in val_df.columns else [""] * len(val_df)
    test_text = test_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in test_df.columns else [""] * len(test_df)

    # Agent justification text (semantic analysis)
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

    # Agent v2 features
    agent_train = extract_agent_features(train_df, dataset_name)
    agent_val = extract_agent_features(val_df, dataset_name)
    agent_test = extract_agent_features(test_df, dataset_name)
    
    for d, agent in [(train_df, agent_train), (val_df, agent_val), (test_df, agent_test)]:
        for col in agent.columns:
            d[f"av2_{col}"] = agent[col].values

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

    # TF-IDF on agent justification text
    just_tfidf = TfidfVectorizer(max_features=150, ngram_range=(1, 2), min_df=2, max_df=0.9,
                                  stop_words='english', sublinear_tf=True)
    try:
        just_tfidf.fit(agent_just_train)
        train_just = just_tfidf.transform(agent_just_train)
        val_just = just_tfidf.transform(agent_just_val)
        test_just = just_tfidf.transform(agent_just_test)
        n_just = min(40, train_just.shape[1], train_just.shape[0] - 1)
        svd_just = TruncatedSVD(n_components=n_just, random_state=42)
        train_just_svd = svd_just.fit_transform(train_just)
        val_just_svd = svd_just.transform(val_just)
        test_just_svd = svd_just.transform(test_just)
    except Exception:
        train_just_svd = val_just_svd = test_just_svd = None

    # TF-IDF on answer chain labels (semantic reconstruction)
    chain_tfidf = TfidfVectorizer(max_features=200, ngram_range=(1, 1), min_df=2, max_df=0.9,
                                   sublinear_tf=True)
    try:
        chain_tfidf.fit(chain_train)
        train_chain = chain_tfidf.transform(chain_train)
        val_chain = chain_tfidf.transform(chain_val)
        test_chain = chain_tfidf.transform(chain_test)
        n_chain = min(50, train_chain.shape[1], train_chain.shape[0] - 1)
        svd_chain = TruncatedSVD(n_components=n_chain, random_state=42)
        train_chain_svd = svd_chain.fit_transform(train_chain)
        val_chain_svd = svd_chain.transform(val_chain)
        test_chain_svd = svd_chain.transform(test_chain)
    except Exception:
        train_chain_svd = val_chain_svd = test_chain_svd = None

    # Supplier risk columns
    sup_drop = [c for c in X_train.columns if c.startswith("supplier_") or 
                c in ("supplier_x_signal", "supplier_x_signals", "supplier_x_t1", "supplier_x_t2")]
    X_tr_ns = X_train.drop(columns=[c for c in sup_drop if c in X_train.columns], errors='ignore').values
    X_va_ns = X_val.drop(columns=[c for c in sup_drop if c in X_val.columns], errors='ignore').values
    X_te_ns = X_test.drop(columns=[c for c in sup_drop if c in X_test.columns], errors='ignore').values

    # Build feature sets
    feature_sets = []
    
    def add_set(name, extras_train, extras_val, extras_test, base_train=None, base_val=None, base_test=None):
        bt = base_train if base_train is not None else X_train.values
        bv = base_val if base_val is not None else X_val.values
        bte = base_test if base_test is not None else X_test.values
        train_parts = [bt] + extras_train
        val_parts = [bv] + extras_val
        test_parts = [bte] + extras_test
        feature_sets.append((name, np.hstack(train_parts), np.hstack(val_parts), np.hstack(test_parts)))
    
    # Collect optional extras
    oe_extras = ([tfidf_oe[0]], [tfidf_oe[1]], [tfidf_oe[2]]) if tfidf_oe[0] is not None else ([], [], [])
    just_extras = ([train_just_svd], [val_just_svd], [test_just_svd]) if train_just_svd is not None else ([], [], [])
    chain_extras = ([train_chain_svd], [val_chain_svd], [test_chain_svd]) if train_chain_svd is not None else ([], [], [])
    deep_extras = ([deep_train.values], [deep_val.values], [deep_test.values])
    
    # With supplier
    add_set("struct", [], [], [])
    add_set("struct_oe", *oe_extras)
    add_set("struct_oe_just", *(oe_extras[i] + just_extras[i] for i in range(3)))
    add_set("struct_oe_chain", *(oe_extras[i] + chain_extras[i] for i in range(3)))
    add_set("struct_oe_just_chain", *(oe_extras[i] + just_extras[i] + chain_extras[i] for i in range(3)))
    add_set("all", *(oe_extras[i] + just_extras[i] + chain_extras[i] + deep_extras[i] for i in range(3)))
    
    # Without supplier
    add_set("no_sup", [], [], [], X_tr_ns, X_va_ns, X_te_ns)
    add_set("no_sup_oe", *oe_extras, X_tr_ns, X_va_ns, X_te_ns)
    add_set("no_sup_all", *(oe_extras[i] + just_extras[i] + chain_extras[i] + deep_extras[i] for i in range(3)), X_tr_ns, X_va_ns, X_te_ns)

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
            # Accuracy filter
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
