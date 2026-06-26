#!/usr/bin/env python3
"""
Experiment 12: Per-dataset feature selection + TF-IDF + calibrated threshold.

The key insight: different datasets need different features. Instead of using
all 156+ features for every dataset, select the top K features per dataset
using mutual information on the training split.

Also: use a more sophisticated threshold search that optimizes F1 directly
with a finer grid and multiple beta values.
"""
from __future__ import annotations
import warnings, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score, fbeta_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_selection import mutual_info_classif, SelectKBest
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
    word_tfidf = TfidfVectorizer(max_features=300, ngram_range=(1, 2), min_df=2, max_df=0.9,
                                  stop_words='english', sublinear_tf=True)
    char_tfidf = TfidfVectorizer(max_features=200, ngram_range=(2, 4), min_df=2, max_df=0.9,
                                  analyzer='char_wb', sublinear_tf=True)
    
    try:
        word_tfidf.fit(train_text)
        char_tfidf.fit(train_text)
        train_w = word_tfidf.transform(train_text)
        val_w = word_tfidf.transform(val_text)
        test_w = word_tfidf.transform(test_text)
        train_c = char_tfidf.transform(train_text)
        val_c = char_tfidf.transform(val_text)
        test_c = char_tfidf.transform(test_text)
        
        n_w = min(80, train_w.shape[1], train_w.shape[0] - 1)
        n_c = min(50, train_c.shape[1], train_c.shape[0] - 1)
        svd_w = TruncatedSVD(n_components=n_w, random_state=42)
        svd_c = TruncatedSVD(n_components=n_c, random_state=42)
        
        train_w_svd = svd_w.fit_transform(train_w)
        val_w_svd = svd_w.transform(val_w)
        test_w_svd = svd_w.transform(test_w)
        train_c_svd = svd_c.fit_transform(train_c)
        val_c_svd = svd_c.transform(val_c)
        test_c_svd = svd_c.transform(test_c)
        
        X_train_comb = np.hstack([X_train.values, train_w_svd, train_c_svd])
        X_val_comb = np.hstack([X_val.values, val_w_svd, val_c_svd])
        X_test_comb = np.hstack([X_test.values, test_w_svd, test_c_svd])
    except Exception:
        X_train_comb = X_train.values
        X_val_comb = X_val.values
        X_test_comb = X_test.values

    # Per-dataset feature selection using mutual information
    n_features = X_train_comb.shape[1]
    n_samples = len(y_train)
    # Select top features: use more features for larger datasets
    k = min(n_features, max(30, n_samples // 3))
    try:
        selector = SelectKBest(score_func=mutual_info_classif, k=k)
        X_train_sel = selector.fit_transform(X_train_comb, y_train)
        X_val_sel = selector.transform(X_val_comb)
        X_test_sel = selector.transform(X_test_comb)
    except Exception:
        X_train_sel = X_train_comb
        X_val_sel = X_val_comb
        X_test_sel = X_test_comb

    n_pos = max((y_train == 1).sum(), 1)
    n_neg = max((y_train == 0).sum(), 1)
    w = np.where(y_train == 1, len(y_train) / (2 * n_pos), len(y_train) / (2 * n_neg))

    # Try multiple model configs
    configs = [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.03, "min_samples_leaf": 15},
        {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.08, "min_samples_leaf": 5},
    ]

    best_f1_val = 0
    best_model = None
    best_iso = None
    best_t = 0.5

    for cfg in configs:
        model = GradientBoostingClassifier(**cfg, subsample=0.8, random_state=42)
        model.fit(X_train_sel, y_train, sample_weight=w)
        
        y_tr_proba = model.predict_proba(X_train_sel)[:, 1]
        iso = IsotonicRegression(out_of_bounds='clip')
        iso.fit(y_tr_proba, y_train)
        
        y_val_cal = iso.transform(model.predict_proba(X_val_sel)[:, 1])
        
        # Try F1, F0.5, and F2 thresholds
        for beta in [0.5, 1.0, 2.0]:
            for t in np.linspace(0.01, 0.99, 500):
                pred = (y_val_cal >= t).astype(int)
                score = fbeta_score(y_val, pred, beta=beta, zero_division=0)
                # Optimize F1 but use F0.5/F2 as tiebreakers for extreme reject rates
                f1 = f1_score(y_val, pred, zero_division=0)
                if f1 > best_f1_val:
                    best_f1_val = f1
                    best_model = model
                    best_iso = iso
                    best_t = t

    y_test_cal = best_iso.transform(best_model.predict_proba(X_test_sel)[:, 1])
    y_test_pred = (y_test_cal >= best_t).astype(int)
    return y_test_pred, y_test_cal
