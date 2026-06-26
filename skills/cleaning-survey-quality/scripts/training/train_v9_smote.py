#!/usr/bin/env python3
"""
Experiment 9: TF-IDF + per-dataset model selection + SMOTE for imbalance.

Uses SMOTE to oversample minority class for datasets with low reject rates.
Tries multiple model configurations and picks the best on validation.
"""
from __future__ import annotations
import warnings, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from imblearn.over_sampling import SMOTE
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from survey_quality_ml import prepare_features

warnings.filterwarnings("ignore")

def train_and_predict(train_df, val_df, test_df):
    train_text = train_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in train_df.columns else [""] * len(train_df)
    val_text = val_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in val_df.columns else [""] * len(val_df)
    test_text = test_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in test_df.columns else [""] * len(test_df)

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

    # TF-IDF
    tfidf = TfidfVectorizer(max_features=300, ngram_range=(1, 2), min_df=2, max_df=0.9,
                            stop_words='english', sublinear_tf=True)
    try:
        tfidf.fit(train_text)
        train_tfidf = tfidf.transform(train_text)
        val_tfidf = tfidf.transform(val_text)
        test_tfidf = tfidf.transform(test_text)
        n_comp = min(80, train_tfidf.shape[1], train_tfidf.shape[0] - 1)
        svd = TruncatedSVD(n_components=n_comp, random_state=42)
        train_tfidf_svd = svd.fit_transform(train_tfidf)
        val_tfidf_svd = svd.transform(val_tfidf)
        test_tfidf_svd = svd.transform(test_tfidf)
        X_train_comb = np.hstack([X_train.values, train_tfidf_svd])
        X_val_comb = np.hstack([X_val.values, val_tfidf_svd])
        X_test_comb = np.hstack([X_test.values, test_tfidf_svd])
    except Exception:
        X_train_comb = X_train.values
        X_val_comb = X_val.values
        X_test_comb = X_test.values

    # SMOTE for class imbalance
    reject_rate = float(y_train.mean())
    try:
        if reject_rate < 0.20 and (y_train == 1).sum() >= 6:
            smote = SMOTE(random_state=42, k_neighbors=min(5, (y_train == 1).sum() - 1))
            X_train_comb, y_train_sm = smote.fit_resample(X_train_comb, y_train)
        else:
            y_train_sm = y_train
    except Exception:
        y_train_sm = y_train

    # Class weights
    n_pos = max((y_train_sm == 1).sum(), 1)
    n_neg = max((y_train_sm == 0).sum(), 1)
    w = np.where(y_train_sm == 1, len(y_train_sm) / (2 * n_pos), len(y_train_sm) / (2 * n_neg))

    # Try multiple model configs, pick best on validation
    configs = [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.03, "min_samples_leaf": 20},
        {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.1, "min_samples_leaf": 5},
        {"n_estimators": 400, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 5},
    ]

    best_f1_val = 0
    best_model = None
    best_iso = None
    best_t = 0.5

    for cfg in configs:
        model = GradientBoostingClassifier(
            **cfg, subsample=0.8, random_state=42
        )
        model.fit(X_train_comb, y_train_sm, sample_weight=w)
        
        y_tr_proba = model.predict_proba(X_train_comb)[:, 1]
        iso = IsotonicRegression(out_of_bounds='clip')
        iso.fit(y_tr_proba, y_train_sm)
        
        y_val_cal = iso.transform(model.predict_proba(X_val_comb)[:, 1])
        for t in np.linspace(0.01, 0.99, 500):
            pred = (y_val_cal >= t).astype(int)
            f1 = f1_score(y_val, pred, zero_division=0)
            if f1 > best_f1_val:
                best_f1_val = f1
                best_model = model
                best_iso = iso
                best_t = t

    y_test_cal = best_iso.transform(best_model.predict_proba(X_test_comb)[:, 1])
    y_test_pred = (y_test_cal >= best_t).astype(int)
    return y_test_pred, y_test_cal
