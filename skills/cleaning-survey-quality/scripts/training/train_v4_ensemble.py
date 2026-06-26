#!/usr/bin/env python3
"""
Experiment 4: Ensemble of GBM + XGBoost + LightGBM with averaged probabilities.
Different models capture different patterns. Averaging reduces overfitting.
"""
from __future__ import annotations
import warnings, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score
import xgboost as xgb
import lightgbm as lgb
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from survey_quality_ml import prepare_features

warnings.filterwarnings("ignore")

def train_and_predict(train_df, val_df, test_df):
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

    n_pos = max((y_train == 1).sum(), 1)
    n_neg = max((y_train == 0).sum(), 1)
    spw = n_neg / n_pos
    w = np.where(y_train == 1, len(y_train) / (2 * n_pos), len(y_train) / (2 * n_neg))

    # Model 1: GradientBoosting
    gbm = GradientBoostingClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, random_state=42, min_samples_leaf=10
    )
    gbm.fit(X_train, y_train, sample_weight=w)

    # Model 2: XGBoost
    xgb_model = xgb.XGBClassifier(
        n_estimators=400, max_depth=5, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=10,
        scale_pos_weight=spw, reg_alpha=0.1, reg_lambda=1.0,
        random_state=42, n_jobs=-1, eval_metric='logloss'
    )
    xgb_model.fit(X_train, y_train)

    # Model 3: LightGBM
    lgb_model = lgb.LGBMClassifier(
        n_estimators=400, max_depth=5, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_samples=10,
        scale_pos_weight=spw, reg_alpha=0.1, reg_lambda=1.0,
        random_state=42, n_jobs=-1, verbose=-1
    )
    lgb_model.fit(X_train, y_train, sample_weight=w)

    # Average probabilities
    p_train = (gbm.predict_proba(X_train)[:, 1] + 
               xgb_model.predict_proba(X_train)[:, 1] + 
               lgb_model.predict_proba(X_train)[:, 1]) / 3
    p_val = (gbm.predict_proba(X_val)[:, 1] + 
             xgb_model.predict_proba(X_val)[:, 1] + 
             lgb_model.predict_proba(X_val)[:, 1]) / 3
    p_test = (gbm.predict_proba(X_test)[:, 1] + 
              xgb_model.predict_proba(X_test)[:, 1] + 
              lgb_model.predict_proba(X_test)[:, 1]) / 3

    # Calibrate
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(p_train, y_train)

    y_val_cal = iso.transform(p_val)
    best_f1, best_t = 0, 0.5
    for t in np.linspace(0.01, 0.99, 500):
        pred = (y_val_cal >= t).astype(int)
        f1 = f1_score(y_val, pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = t

    y_test_cal = iso.transform(p_test)
    y_test_pred = (y_test_cal >= best_t).astype(int)
    return y_test_pred, y_test_cal
