#!/usr/bin/env python3
"""
Experiment 5: Per-dataset adaptive approach.

For low-reject datasets (under 10%): use raw data only, no supplier risk
For high-reject datasets (over 30%): use all features with aggressive threshold
For medium datasets: use all features with F1-optimal threshold

Also: per-dataset threshold strategy.
For low-reject: optimize F0.5 (precision-weighted) to avoid false positives
For high-reject: optimize F2 (recall-weighted) to catch more bad respondents
For medium: optimize F1 (balanced)
"""
from __future__ import annotations
import warnings, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import fbeta_score, f1_score
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from survey_quality_ml import prepare_features

warnings.filterwarnings("ignore")

def train_and_predict(train_df, val_df, test_df):
    X_train, y_train = prepare_features(train_df)
    X_val, y_val = prepare_features(val_df)
    X_test, y_test = prepare_features(test_df)

    # Determine dataset characteristics from training data
    reject_rate = float(y_train.mean())
    is_low_reject = reject_rate < 0.10
    is_high_reject = reject_rate > 0.30

    # Feature selection based on reject rate
    if is_low_reject:
        # Remove supplier risk for low-reject datasets (leakage audit showed this helps)
        drop_cols = [c for c in X_train.columns if c.startswith("supplier_") or 
                     c in ("supplier_x_signals", "supplier_x_t1", "supplier_x_t2")]
        X_train = X_train.drop(columns=drop_cols, errors='ignore')
        X_val = X_val.drop(columns=[c for c in drop_cols if c in X_val.columns], errors='ignore')
        X_test = X_test.drop(columns=[c for c in drop_cols if c in X_test.columns], errors='ignore')

    # Align columns
    for c in X_train.columns:
        if c not in X_val.columns: X_val[c] = 0
        if c not in X_test.columns: X_test[c] = 0
    for c in X_val.columns:
        if c not in X_train.columns: X_train[c] = 0
    for c in X_test.columns:
        if c not in X_train.columns: X_train[c] = 0
    X_val = X_val[X_train.columns]
    X_test = X_test[X_train.columns]

    # Class weights
    n_pos = max((y_train == 1).sum(), 1)
    n_neg = max((y_train == 0).sum(), 1)
    w = np.where(y_train == 1, len(y_train) / (2 * n_pos), len(y_train) / (2 * n_neg))

    # Model hyperparameters based on dataset size and reject rate
    if is_low_reject:
        # More conservative: deeper trees, more regularization
        model = GradientBoostingClassifier(
            n_estimators=500, max_depth=3, learning_rate=0.03,
            subsample=0.7, random_state=42, min_samples_leaf=20,
            max_features='sqrt'
        )
    elif is_high_reject:
        # More aggressive: shallower trees, faster learning
        model = GradientBoostingClassifier(
            n_estimators=400, max_depth=5, learning_rate=0.08,
            subsample=0.8, random_state=42, min_samples_leaf=5
        )
    else:
        model = GradientBoostingClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.8, random_state=42, min_samples_leaf=10
        )

    model.fit(X_train, y_train, sample_weight=w)

    # Calibrate
    y_train_proba = model.predict_proba(X_train)[:, 1]
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(y_train_proba, y_train)

    # Threshold optimization based on reject rate
    y_val_cal = iso.transform(model.predict_proba(X_val)[:, 1])
    
    if is_low_reject:
        # F0.5: precision-weighted (avoid false positives in low-reject datasets)
        beta = 0.5
    elif is_high_reject:
        # F2: recall-weighted (catch more bad respondents in high-reject datasets)
        beta = 2.0
    else:
        # F1: balanced
        beta = 1.0

    best_score, best_t = 0, 0.5
    for t in np.linspace(0.01, 0.99, 500):
        pred = (y_val_cal >= t).astype(int)
        score = fbeta_score(y_val, pred, beta=beta, zero_division=0)
        if score > best_score:
            best_score = score
            best_t = t

    y_test_cal = iso.transform(model.predict_proba(X_test)[:, 1])
    y_test_pred = (y_test_cal >= best_t).astype(int)
    return y_test_pred, y_test_cal
