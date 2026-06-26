#!/usr/bin/env python3
"""
Experiment 8: TF-IDF text features + structured features + per-dataset strategy.

Adds TF-IDF features from open-end text content (not just aggregate stats).
Fits TF-IDF on train, transforms val and test.
Combines with structured features and uses F1-optimal threshold.
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

warnings.filterwarnings("ignore")

def train_and_predict(train_df, val_df, test_df):
    # Get raw text
    train_text = train_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in train_df.columns else [""] * len(train_df)
    val_text = val_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in val_df.columns else [""] * len(val_df)
    test_text = test_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in test_df.columns else [""] * len(test_df)

    # Structured features
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
    tfidf = TfidfVectorizer(
        max_features=200, ngram_range=(1, 2), min_df=2, max_df=0.9,
        stop_words='english', sublinear_tf=True
    )
    try:
        tfidf.fit(train_text)
        train_tfidf = tfidf.transform(train_text)
        val_tfidf = tfidf.transform(val_text)
        test_tfidf = tfidf.transform(test_text)
        
        # Reduce dimensionality with SVD
        n_comp = min(50, train_tfidf.shape[1], train_tfidf.shape[0] - 1)
        svd = TruncatedSVD(n_components=n_comp, random_state=42)
        train_tfidf_svd = svd.fit_transform(train_tfidf)
        val_tfidf_svd = svd.transform(val_tfidf)
        test_tfidf_svd = svd.transform(test_tfidf)
        
        # Combine
        X_train = np.hstack([X_train.values, train_tfidf_svd])
        X_val = np.hstack([X_val.values, val_tfidf_svd])
        X_test = np.hstack([X_test.values, test_tfidf_svd])
    except Exception:
        X_train = X_train.values
        X_val = X_val.values
        X_test = X_test.values

    # Class weights
    n_pos = max((y_train == 1).sum(), 1)
    n_neg = max((y_train == 0).sum(), 1)
    w = np.where(y_train == 1, len(y_train) / (2 * n_pos), len(y_train) / (2 * n_neg))

    model = GradientBoostingClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, random_state=42, min_samples_leaf=10
    )
    model.fit(X_train, y_train, sample_weight=w)

    y_train_proba = model.predict_proba(X_train)[:, 1]
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(y_train_proba, y_train)

    y_val_cal = iso.transform(model.predict_proba(X_val)[:, 1])
    best_f1, best_t = 0, 0.5
    for t in np.linspace(0.01, 0.99, 500):
        pred = (y_val_cal >= t).astype(int)
        f1 = f1_score(y_val, pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = t

    y_test_cal = iso.transform(model.predict_proba(X_test)[:, 1])
    y_test_pred = (y_test_cal >= best_t).astype(int)
    return y_test_pred, y_test_cal
