#!/usr/bin/env python3
"""
Experiment 22: Two-stage ML + Agent fusion pipeline.

ARCHITECTURE:
  Stage 1: ML model on structured features → risk probability per respondent
  Stage 2: Agent fusion model that takes:
    - ML probability (from stage 1)
    - Agent v2 blind run signals (unbiased agent components)
    - Semantic reconstruction (answer chain text TF-IDF)
    - Agent justification text TF-IDF
    → Final discard/keep decision

The agent v2 ran BLIND (no labels), providing unbiased signal components.
The ML model provides calibrated risk scores. The fusion model combines
both for the final decision.

This is the "agent analysis after ML run for final decision pass" architecture.
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
    load_agent_determinations,
)

warnings.filterwarnings("ignore")


def stage1_ml(train_df, val_df, test_df, train_text, val_text, test_text):
    """Stage 1: ML model on structured features → probabilities."""
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

    # TF-IDF on open-end text
    tfidf_oe = get_tfidf_features(train_text, val_text, test_text, word=True, char=True)

    # Try with and without TF-IDF
    approaches = []
    
    configs = [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.03, "min_samples_leaf": 15},
    ]

    # Structured only
    for cfg in configs:
        m, iso, t, f1 = train_gbm(X_train.values, y_train, X_val.values, y_val, cfg)
        approaches.append(("struct", m, iso, t, f1, X_train.values, X_val.values, X_test.values))

    # Structured + TF-IDF
    if tfidf_oe[0] is not None:
        X_tr = np.hstack([X_train.values, tfidf_oe[0]])
        X_va = np.hstack([X_val.values, tfidf_oe[1]])
        X_te = np.hstack([X_test.values, tfidf_oe[2]])
        for cfg in configs:
            m, iso, t, f1 = train_gbm(X_tr, y_train, X_va, y_val, cfg)
            approaches.append(("struct_tfidf", m, iso, t, f1, X_tr, X_va, X_te))

    best = max(approaches, key=lambda a: a[4])
    name, model, iso, best_t, best_f1, _, _, X_te = best

    # Get probabilities for all splits
    train_proba = iso.transform(model.predict_proba(best[5])[:, 1])
    val_proba = iso.transform(model.predict_proba(best[6])[:, 1])
    test_proba = iso.transform(model.predict_proba(X_te)[:, 1])

    return train_proba, val_proba, test_proba, best_t


def stage2_agent_fusion(train_df, val_df, test_df, train_proba, val_proba, test_proba,
                        dataset_name, train_text, val_text, test_text):
    """Stage 2: Agent fusion model combining ML probability + agent signals + semantic reconstruction."""
    
    # Agent v2 features
    agent_train = extract_agent_features(train_df, dataset_name).fillna(0)
    agent_val = extract_agent_features(val_df, dataset_name).fillna(0)
    agent_test = extract_agent_features(test_df, dataset_name).fillna(0)

    # Agent justification text TF-IDF
    agent_just_train = get_agent_justification_text(train_df, dataset_name)
    agent_just_val = get_agent_justification_text(val_df, dataset_name)
    agent_just_test = get_agent_justification_text(test_df, dataset_name)

    # Answer chain text (semantic reconstruction)
    chain_train = get_answer_chain_text(train_df, dataset_name)
    chain_val = get_answer_chain_text(val_df, dataset_name)
    chain_test = get_answer_chain_text(test_df, dataset_name)

    # TF-IDF on agent justification
    just_svd_train = just_svd_val = just_svd_test = None
    try:
        just_tfidf = TfidfVectorizer(max_features=150, ngram_range=(1, 2), min_df=2, max_df=0.9,
                                      stop_words='english', sublinear_tf=True)
        just_tfidf.fit(agent_just_train)
        jt = just_tfidf.transform(agent_just_train)
        jv = just_tfidf.transform(agent_just_val)
        jte = just_tfidf.transform(agent_just_test)
        n = min(30, jt.shape[1], jt.shape[0] - 1)
        svd = TruncatedSVD(n_components=n, random_state=42)
        just_svd_train = svd.fit_transform(jt)
        just_svd_val = svd.transform(jv)
        just_svd_test = svd.transform(jte)
    except Exception:
        pass

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

    # Build stage 2 feature matrix
    # Core: ML probability + agent v2 features
    parts_train = [train_proba.reshape(-1, 1), agent_train.values]
    parts_val = [val_proba.reshape(-1, 1), agent_val.values]
    parts_test = [test_proba.reshape(-1, 1), agent_test.values]

    # Add semantic features if available
    if just_svd_train is not None:
        parts_train.append(just_svd_train)
        parts_val.append(just_svd_val)
        parts_test.append(just_svd_test)
    if chain_svd_train is not None:
        parts_train.append(chain_svd_train)
        parts_val.append(chain_svd_val)
        parts_test.append(chain_svd_test)

    X2_train = np.hstack(parts_train)
    X2_val = np.hstack(parts_val)
    X2_test = np.hstack(parts_test)

    y_train = train_df["label"].values
    y_val = val_df["label"].values
    y_test = test_df["label"].values

    # Also try ML-probability-only and agent-only as baselines
    configs = [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.03, "min_samples_leaf": 15},
        {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.08, "min_samples_leaf": 5},
    ]

    approaches = []

    # ML prob only (stage 1 baseline)
    for cfg in configs:
        m, iso, t, f1 = train_gbm(train_proba.reshape(-1, 1), y_train, val_proba.reshape(-1, 1), y_val, cfg)
        approaches.append(("ml_only", m, iso, t, f1, train_proba.reshape(-1, 1), val_proba.reshape(-1, 1), test_proba.reshape(-1, 1)))

    # Agent only
    for cfg in configs:
        m, iso, t, f1 = train_gbm(agent_train.values, y_train, agent_val.values, y_val, cfg)
        approaches.append(("agent_only", m, iso, t, f1, agent_train.values, agent_val.values, agent_test.values))

    # ML + Agent
    ml_agent_train = np.hstack([train_proba.reshape(-1, 1), agent_train.values])
    ml_agent_val = np.hstack([val_proba.reshape(-1, 1), agent_val.values])
    ml_agent_test = np.hstack([test_proba.reshape(-1, 1), agent_test.values])
    for cfg in configs:
        m, iso, t, f1 = train_gbm(ml_agent_train, y_train, ml_agent_val, y_val, cfg)
        approaches.append(("ml_agent", m, iso, t, f1, ml_agent_train, ml_agent_val, ml_agent_test))

    # Full fusion: ML + Agent + Semantic
    for cfg in configs:
        m, iso, t, f1 = train_gbm(X2_train, y_train, X2_val, y_val, cfg)
        approaches.append(("full_fusion", m, iso, t, f1, X2_train, X2_val, X2_test))

    # Pick best
    best = max(approaches, key=lambda a: a[4])
    name, model, iso, best_t, best_f1, _, _, X_te = best

    y_test_cal = iso.transform(model.predict_proba(X_te)[:, 1])
    y_test_pred = (y_test_cal >= best_t).astype(int)
    return y_test_pred, y_test_cal, name


def train_and_predict(train_df, val_df, test_df):
    dataset_name = train_df["dataset"].iloc[0] if "dataset" in train_df.columns else ""
    
    # Work on copies
    train_df = train_df.copy()
    val_df = val_df.copy()
    test_df = test_df.copy()

    train_text = train_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in train_df.columns else [""] * len(train_df)
    val_text = val_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in val_df.columns else [""] * len(val_df)
    test_text = test_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in test_df.columns else [""] * len(test_df)

    # Add raw Excel features
    raw_train = extract_raw_excel_features(dataset_name, train_df["respondent_id"].values)
    raw_val = extract_raw_excel_features(dataset_name, val_df["respondent_id"].values)
    raw_test = extract_raw_excel_features(dataset_name, test_df["respondent_id"].values)
    
    for d, raw in [(train_df, raw_train), (val_df, raw_val), (test_df, raw_test)]:
        if len(raw) > 0:
            raw_indexed = raw.set_index("respondent_id")
            for col in raw_indexed.columns:
                d[f"raw_{col}"] = d["respondent_id"].map(raw_indexed[col]).fillna(0)

    # Stage 1: ML
    train_proba, val_proba, test_proba, stage1_t = stage1_ml(
        train_df, val_df, test_df, train_text, val_text, test_text)

    # Stage 2: Agent fusion
    y_pred, y_proba, stage2_name = stage2_agent_fusion(
        train_df, val_df, test_df, train_proba, val_proba, test_proba,
        dataset_name, train_text, val_text, test_text)

    return y_pred, y_proba
