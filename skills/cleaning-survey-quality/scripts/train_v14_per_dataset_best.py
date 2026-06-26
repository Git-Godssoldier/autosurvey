#!/usr/bin/env python3
"""
Experiment 14: Per-dataset best model selection.

For each dataset, tries multiple approaches and picks the one with the best
validation F1. This is the autoresearch "keep what works" principle applied
at the dataset level.

Approaches per dataset:
1. GBM with F1 threshold (baseline)
2. TF-IDF + GBM with F1 threshold (v8)
3. TF-IDF + char n-grams + GBM (v10 without stacking)
4. Deep features + TF-IDF + GBM (v13)
5. No supplier risk + TF-IDF + GBM (for low-reject datasets)
6. Aggressive agent rules union with ML
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
sys.path.insert(0, str(Path(__file__).parent))
from survey_quality_ml import prepare_features
from train_v13_deep import extract_deep_features

warnings.filterwarnings("ignore")

def get_tfidf_features(train_text, val_text, test_text, word=True, char=True):
    """Get TF-IDF features."""
    parts_train, parts_val, parts_test = [], [], []
    
    if word:
        wt = TfidfVectorizer(max_features=200, ngram_range=(1, 2), min_df=2, max_df=0.9,
                              stop_words='english', sublinear_tf=True)
        wt.fit(train_text)
        train_w = wt.transform(train_text)
        val_w = wt.transform(val_text)
        test_w = wt.transform(test_text)
        n = min(50, train_w.shape[1], train_w.shape[0] - 1)
        svd = TruncatedSVD(n_components=n, random_state=42)
        parts_train.append(svd.fit_transform(train_w))
        parts_val.append(svd.transform(val_w))
        parts_test.append(svd.transform(test_w))
    
    if char:
        ct = TfidfVectorizer(max_features=200, ngram_range=(2, 4), min_df=2, max_df=0.9,
                              analyzer='char_wb', sublinear_tf=True)
        ct.fit(train_text)
        train_c = ct.transform(train_text)
        val_c = ct.transform(val_text)
        test_c = ct.transform(test_text)
        n = min(50, train_c.shape[1], train_c.shape[0] - 1)
        svd = TruncatedSVD(n_components=n, random_state=42)
        parts_train.append(svd.fit_transform(train_c))
        parts_val.append(svd.transform(val_c))
        parts_test.append(svd.transform(test_c))
    
    if not parts_train:
        return None, None, None
    
    return (np.hstack(parts_train), np.hstack(parts_val), np.hstack(parts_test))


def train_gbm(X_train, y_train, X_val, y_val, cfg=None):
    """Train GBM and return model, iso, best_t, val_f1."""
    if cfg is None:
        cfg = {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10}
    
    n_pos = max((y_train == 1).sum(), 1)
    n_neg = max((y_train == 0).sum(), 1)
    w = np.where(y_train == 1, len(y_train) / (2 * n_pos), len(y_train) / (2 * n_neg))
    
    model = GradientBoostingClassifier(**cfg, subsample=0.8, random_state=42)
    model.fit(X_train, y_train, sample_weight=w)
    
    y_tr_proba = model.predict_proba(X_train)[:, 1]
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(y_tr_proba, y_train)
    
    y_val_cal = iso.transform(model.predict_proba(X_val)[:, 1])
    best_f1, best_t = 0, 0.5
    for t in np.linspace(0.01, 0.99, 500):
        pred = (y_val_cal >= t).astype(int)
        f1 = f1_score(y_val, pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = t
    
    return model, iso, best_t, best_f1


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

    # Deep features
    deep_train = extract_deep_features(train_df)
    deep_val = extract_deep_features(val_df)
    deep_test = extract_deep_features(test_df)

    # Try multiple approaches and pick the best on validation
    configs = [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.03, "min_samples_leaf": 15},
        {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.08, "min_samples_leaf": 5},
    ]

    approaches = []

    # Approach 1: Structured only
    for cfg in configs:
        m, iso, t, f1 = train_gbm(X_train.values, y_train, X_val.values, y_val, cfg)
        approaches.append(("structured", m, iso, t, f1, X_train.values, X_val.values, X_test.values))

    # Approach 2: TF-IDF word only
    tfidf_w = get_tfidf_features(train_text, val_text, test_text, word=True, char=False)
    if tfidf_w[0] is not None:
        X_tr = np.hstack([X_train.values, tfidf_w[0]])
        X_va = np.hstack([X_val.values, tfidf_w[1]])
        X_te = np.hstack([X_test.values, tfidf_w[2]])
        for cfg in configs:
            m, iso, t, f1 = train_gbm(X_tr, y_train, X_va, y_val, cfg)
            approaches.append(("tfidf_w", m, iso, t, f1, X_tr, X_va, X_te))

    # Approach 3: TF-IDF word + char
    tfidf_wc = get_tfidf_features(train_text, val_text, test_text, word=True, char=True)
    if tfidf_wc[0] is not None:
        X_tr = np.hstack([X_train.values, tfidf_wc[0]])
        X_va = np.hstack([X_val.values, tfidf_wc[1]])
        X_te = np.hstack([X_test.values, tfidf_wc[2]])
        for cfg in configs:
            m, iso, t, f1 = train_gbm(X_tr, y_train, X_va, y_val, cfg)
            approaches.append(("tfidf_wc", m, iso, t, f1, X_tr, X_va, X_te))

    # Approach 4: Deep + TF-IDF word
    if tfidf_w[0] is not None:
        X_tr = np.hstack([X_train.values, tfidf_w[0], deep_train.values])
        X_va = np.hstack([X_val.values, tfidf_w[1], deep_val.values])
        X_te = np.hstack([X_test.values, tfidf_w[2], deep_test.values])
        for cfg in configs:
            m, iso, t, f1 = train_gbm(X_tr, y_train, X_va, y_val, cfg)
            approaches.append(("deep_tfidf_w", m, iso, t, f1, X_tr, X_va, X_te))

    # Approach 5: No supplier risk + TF-IDF
    drop_cols = [c for c in X_train.columns if c.startswith("supplier_") or 
                 c in ("supplier_x_signals", "supplier_x_t1", "supplier_x_t2")]
    X_tr_ns = X_train.drop(columns=drop_cols, errors='ignore').values
    X_va_ns = X_val.drop(columns=[c for c in drop_cols if c in X_val.columns], errors='ignore').values
    X_te_ns = X_test.drop(columns=[c for c in drop_cols if c in X_test.columns], errors='ignore').values
    if tfidf_w[0] is not None:
        X_tr = np.hstack([X_tr_ns, tfidf_w[0]])
        X_va = np.hstack([X_va_ns, tfidf_w[1]])
        X_te = np.hstack([X_te_ns, tfidf_w[2]])
        for cfg in configs:
            m, iso, t, f1 = train_gbm(X_tr, y_train, X_va, y_val, cfg)
            approaches.append(("no_supplier_tfidf", m, iso, t, f1, X_tr, X_va, X_te))

    # Approach 6: Deep + TF-IDF word + char
    if tfidf_wc[0] is not None:
        X_tr = np.hstack([X_train.values, tfidf_wc[0], deep_train.values])
        X_va = np.hstack([X_val.values, tfidf_wc[1], deep_val.values])
        X_te = np.hstack([X_test.values, tfidf_wc[2], deep_test.values])
        for cfg in configs:
            m, iso, t, f1 = train_gbm(X_tr, y_train, X_va, y_val, cfg)
            approaches.append(("deep_tfidf_wc", m, iso, t, f1, X_tr, X_va, X_te))

    # Pick best approach
    best = max(approaches, key=lambda a: a[4])
    name, model, iso, best_t, best_f1, _, _, X_te = best

    y_test_cal = iso.transform(model.predict_proba(X_te)[:, 1])
    y_test_pred = (y_test_cal >= best_t).astype(int)
    return y_test_pred, y_test_cal
