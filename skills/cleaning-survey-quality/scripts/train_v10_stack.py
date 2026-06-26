#!/usr/bin/env python3
"""
Experiment 10: TF-IDF + character n-grams + stacking ensemble.

Adds character-level TF-IDF to catch spam/bot patterns (repeated chars, 
non-English text, keyboard mashing). Uses stacking with logistic regression
meta-learner to combine multiple base models.
"""
from __future__ import annotations
import warnings, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
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

    # Word-level TF-IDF
    word_tfidf = TfidfVectorizer(max_features=200, ngram_range=(1, 2), min_df=2, max_df=0.9,
                                  stop_words='english', sublinear_tf=True)
    # Char-level TF-IDF (catches spam patterns, non-English, keyboard mashing)
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
        
        # SVD on each
        n_w = min(50, train_w.shape[1], train_w.shape[0] - 1)
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

    # Class weights
    n_pos = max((y_train == 1).sum(), 1)
    n_neg = max((y_train == 0).sum(), 1)
    w = np.where(y_train == 1, len(y_train) / (2 * n_pos), len(y_train) / (2 * n_neg))

    # Base models with different configurations
    models = []
    for cfg in [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.03, "min_samples_leaf": 15},
    ]:
        m = GradientBoostingClassifier(**cfg, subsample=0.8, random_state=42)
        m.fit(X_train_comb, y_train, sample_weight=w)
        models.append(m)

    # Get base model predictions for stacking
    train_meta = np.column_stack([m.predict_proba(X_train_comb)[:, 1] for m in models])
    val_meta = np.column_stack([m.predict_proba(X_val_comb)[:, 1] for m in models])
    test_meta = np.column_stack([m.predict_proba(X_test_comb)[:, 1] for m in models])

    # Meta-learner
    meta = LogisticRegression(C=1.0, random_state=42, class_weight='balanced')
    meta.fit(train_meta, y_train)

    # Calibrate
    y_train_proba = meta.predict_proba(train_meta)[:, 1]
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(y_train_proba, y_train)

    y_val_cal = iso.transform(meta.predict_proba(val_meta)[:, 1])
    best_f1, best_t = 0, 0.5
    for t in np.linspace(0.01, 0.99, 500):
        pred = (y_val_cal >= t).astype(int)
        f1 = f1_score(y_val, pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = t

    y_test_cal = iso.transform(meta.predict_proba(test_meta)[:, 1])
    y_test_pred = (y_test_cal >= best_t).astype(int)
    return y_test_pred, y_test_cal
