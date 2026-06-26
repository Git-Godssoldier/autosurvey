#!/usr/bin/env python3
"""
Experiment 17: Ultimate ensemble — all feature types + per-dataset selection.

Combines ALL feature types we've developed:
1. Structured features (156 from Excel extraction)
2. Raw Excel per-question answer patterns
3. Deep answer-chain features (interactions, composites)
4. Word-level TF-IDF on open-end text
5. Char-level TF-IDF on open-end text (spam/bot patterns)
6. Agent description TF-IDF (post-signal agent analysis text)
7. Per-dataset model selection (6 feature sets x 3 configs = 18 approaches)

Also adds: for each approach, try both with and without supplier risk.
"""
from __future__ import annotations
import warnings, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from survey_quality_ml import prepare_features
from train_v13_deep import extract_deep_features
from train_v14_per_dataset_best import get_tfidf_features, train_gbm
from train_v15_raw_excel import extract_raw_excel_features
from train_v16_agent_text import generate_agent_description

warnings.filterwarnings("ignore")

def train_and_predict(train_df, val_df, test_df):
    train_text = train_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in train_df.columns else [""] * len(train_df)
    val_text = val_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in val_df.columns else [""] * len(val_df)
    test_text = test_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in test_df.columns else [""] * len(test_df)

    # Add raw Excel features
    dataset_name = train_df["dataset"].iloc[0] if "dataset" in train_df.columns else ""
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

    # Deep features
    deep_train = extract_deep_features(train_df)
    deep_val = extract_deep_features(val_df)
    deep_test = extract_deep_features(test_df)

    # TF-IDF on open-end text
    tfidf_oe = get_tfidf_features(train_text, val_text, test_text, word=True, char=True)
    
    # Agent description TF-IDF
    agent_train_text = generate_agent_description(train_df)
    agent_val_text = generate_agent_description(val_df)
    agent_test_text = generate_agent_description(test_df)
    
    agent_tfidf = TfidfVectorizer(max_features=100, ngram_range=(1, 1), min_df=1, max_df=0.95,
                                   sublinear_tf=True, binary=True)
    try:
        agent_tfidf.fit(agent_train_text)
        train_agent = agent_tfidf.transform(agent_train_text).toarray()
        val_agent = agent_tfidf.transform(agent_val_text).toarray()
        test_agent = agent_tfidf.transform(agent_test_text).toarray()
    except Exception:
        train_agent = val_agent = test_agent = None

    # Supplier risk columns to optionally drop
    sup_drop = [c for c in X_train.columns if c.startswith("supplier_") or 
                c in ("supplier_x_signal", "supplier_x_signals", "supplier_x_t1", "supplier_x_t2")]
    
    # Build feature sets
    feature_sets = []
    
    def add_set(name, extra_train, extra_val, extra_test, base_train=None, base_val=None, base_test=None):
        bt = base_train if base_train is not None else X_train.values
        bv = base_val if base_val is not None else X_val.values
        bte = base_test if base_test is not None else X_test.values
        if extra_train is not None:
            feature_sets.append((name,
                np.hstack([bt, extra_train]),
                np.hstack([bv, extra_val]),
                np.hstack([bte, extra_test])))
        else:
            feature_sets.append((name, bt, bv, bte))
    
    # With supplier
    add_set("struct", None, None, None)
    if tfidf_oe[0] is not None:
        add_set("struct_tfidf", tfidf_oe[0], tfidf_oe[1], tfidf_oe[2])
    if train_agent is not None:
        add_set("struct_agent", train_agent, val_agent, test_agent)
    if tfidf_oe[0] is not None and train_agent is not None:
        add_set("struct_tfidf_agent", np.hstack([tfidf_oe[0], train_agent]), 
                np.hstack([tfidf_oe[1], val_agent]), np.hstack([tfidf_oe[2], test_agent]))
    if tfidf_oe[0] is not None and train_agent is not None:
        add_set("all", np.hstack([tfidf_oe[0], train_agent, deep_train.values]),
                np.hstack([tfidf_oe[1], val_agent, deep_val.values]),
                np.hstack([tfidf_oe[2], test_agent, deep_test.values]))
    
    # Without supplier
    X_tr_ns = X_train.drop(columns=[c for c in sup_drop if c in X_train.columns], errors='ignore').values
    X_va_ns = X_val.drop(columns=[c for c in sup_drop if c in X_val.columns], errors='ignore').values
    X_te_ns = X_test.drop(columns=[c for c in sup_drop if c in X_test.columns], errors='ignore').values
    
    add_set("no_sup", None, None, None, X_tr_ns, X_va_ns, X_te_ns)
    if tfidf_oe[0] is not None:
        add_set("no_sup_tfidf", tfidf_oe[0], tfidf_oe[1], tfidf_oe[2], X_tr_ns, X_va_ns, X_te_ns)
    if train_agent is not None:
        add_set("no_sup_agent", train_agent, val_agent, test_agent, X_tr_ns, X_va_ns, X_te_ns)
    if tfidf_oe[0] is not None and train_agent is not None:
        add_set("no_sup_all", np.hstack([tfidf_oe[0], train_agent, deep_train.values]),
                np.hstack([tfidf_oe[1], val_agent, deep_val.values]),
                np.hstack([tfidf_oe[2], test_agent, deep_test.values]),
                X_tr_ns, X_va_ns, X_te_ns)

    configs = [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.03, "min_samples_leaf": 15},
        {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.08, "min_samples_leaf": 5},
    ]

    approaches = []
    for name, X_tr, X_va, X_te in feature_sets:
        for cfg in configs:
            m, iso, t, f1 = train_gbm(X_tr, y_train, X_va, y_val, cfg)
            approaches.append((name, m, iso, t, f1, X_tr, X_va, X_te))

    # Pick best
    best = max(approaches, key=lambda a: a[4])
    name, model, iso, best_t, best_f1, _, _, X_te = best

    y_test_cal = iso.transform(model.predict_proba(X_te)[:, 1])
    y_test_pred = (y_test_cal >= best_t).astype(int)
    return y_test_pred, y_test_cal
