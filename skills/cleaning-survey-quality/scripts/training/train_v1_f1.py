#!/usr/bin/env python3
"""
Survey quality training script — MODIFY THIS to improve F1.

The eval_harness.py imports this and calls train_and_predict().
You can change anything in this file: model, features, threshold, rules.

Current approach: Gradient Boosting with F1-optimal threshold.
"""
from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score, accuracy_score

warnings.filterwarnings("ignore")

# Import shared utilities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from survey_quality_ml import prepare_features


def train_and_predict(train_df, val_df, test_df):
    """Train on train_df, tune on val_df, predict on test_df.
    
    Returns:
        y_pred: binary predictions (0=keep, 1=discard)
        y_proba: probability scores (0 to 1)
    """
    X_train, y_train = prepare_features(train_df)
    X_val, y_val = prepare_features(val_df)
    X_test, y_test = prepare_features(test_df)

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

    # Train model
    model = GradientBoostingClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, random_state=42, min_samples_leaf=10
    )
    model.fit(X_train, y_train, sample_weight=w)

    # Calibrate
    y_train_proba = model.predict_proba(X_train)[:, 1]
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(y_train_proba, y_train)

    # Tune threshold on validation — OPTIMIZE F1 NOT ACCURACY
    y_val_proba = model.predict_proba(X_val)[:, 1]
    y_val_cal = iso.transform(y_val_proba)
    best_f1, best_t = 0, 0.5
    for t in np.linspace(0.01, 0.99, 500):
        pred = (y_val_cal >= t).astype(int)
        f1 = f1_score(y_val, pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = t

    # Predict on test
    y_test_proba = model.predict_proba(X_test)[:, 1]
    y_test_cal = iso.transform(y_test_proba)
    y_test_pred = (y_test_cal >= best_t).astype(int)

    return y_test_pred, y_test_cal
