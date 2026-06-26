#!/usr/bin/env python3
"""
Experiment 7: Per-dataset strategy selection + aggressive agent rules union.

For each dataset, pick the best strategy based on validation performance:
1. ML only (F1-optimal threshold)
2. Rules only (aggressive thresholds)
3. Union of ML + rules (discard if either says discard)
4. Intersection of ML + rules (discard only if both agree)

Also: make agent rules more aggressive by lowering signal count thresholds
and adding new rules based on the per-dataset signal analysis.
"""
from __future__ import annotations
import warnings, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score, precision_score, recall_score
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from survey_quality_ml import prepare_features

warnings.filterwarnings("ignore")

def aggressive_agent_rules(df):
    """More aggressive agent rules based on per-dataset signal analysis."""
    determinations = []
    risk_scores = []
    
    for _, row in df.iterrows():
        risk = 0.0
        det = "KEEP"
        
        # TIER 1: auto-discard
        if row.get("t1_count", 0) > 0:
            det = "DISCARD"
            risk += 0.4
        
        # High signal count (lowered from 5 to 3)
        if row.get("signal_count", 0) >= 3:
            risk += 0.2
            if det == "KEEP": det = "REVIEW"
        if row.get("signal_count", 0) >= 5:
            risk += 0.2
            if det != "DISCARD": det = "REVIEW"
        
        # TIER 2 signals
        if row.get("t2_count", 0) > 0:
            risk += 0.15
            if det == "KEEP": det = "REVIEW"
        
        # Matrix straightline (lowered threshold)
        if row.get("matrix_straightline", 0) == 1:
            risk += 0.15
            if det == "KEEP": det = "REVIEW"
        if row.get("matrix_near_straightline", 0) == 1 and row.get("matrix_count", 0) >= 5:
            risk += 0.1
            if det == "KEEP": det = "REVIEW"
        
        # Open-end quality
        if row.get("oe_very_short", 0) == 1:
            risk += 0.15
            if det == "KEEP": det = "REVIEW"
        if row.get("oe_short", 0) == 1:
            risk += 0.05
        if row.get("oe_generic", 0) == 1:
            risk += 0.1
        if row.get("oe_has_none", 0) == 1:
            risk += 0.1
        if row.get("oe_all_caps", 0) == 1:
            risk += 0.1
        
        # Timing (lowered z-score threshold)
        if row.get("qtime_seconds_zscore", 0) < -1.0:
            risk += 0.15
            if det == "KEEP": det = "REVIEW"
        if row.get("qtime_seconds_zscore", 0) < -1.5:
            risk += 0.1
            if det != "DISCARD": det = "REVIEW"
        
        # Duplicates
        if row.get("oe_is_dup", 0) == 1:
            risk += 0.1
        if row.get("ip_is_dup", 0) == 1:
            risk += 0.15
            if det == "KEEP": det = "REVIEW"
        if row.get("ua_is_dup", 0) == 1:
            risk += 0.1
        
        # Supplier risk
        if row.get("supplier_reject_rate", 0) > 0.3:
            risk += 0.1
        if row.get("supplier_missing", 0) == 1:
            risk += 0.1
        
        # LangAssess abnormal
        if "lang_LangAssessReadLevel" in row and row["lang_LangAssessReadLevel"] > 10:
            risk += 0.1
            if det == "KEEP": det = "REVIEW"
        
        # Coded answer diversity
        if row.get("coded_dk_ratio", 0) > 0.3:
            risk += 0.1
        if row.get("coded_unique_ratio", 0) < 0.3:
            risk += 0.05
        
        determinations.append(det)
        risk_scores.append(risk)
    
    return pd.DataFrame({"determination": determinations, "risk_score": risk_scores})


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
    w = np.where(y_train == 1, len(y_train) / (2 * n_pos), len(y_train) / (2 * n_neg))

    model = GradientBoostingClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, random_state=42, min_samples_leaf=10
    )
    model.fit(X_train, y_train, sample_weight=w)

    y_train_proba = model.predict_proba(X_train)[:, 1]
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(y_train_proba, y_train)

    # Get ML predictions for val and test at F1-optimal threshold
    y_val_cal = iso.transform(model.predict_proba(X_val)[:, 1])
    best_f1, best_t = 0, 0.5
    for t in np.linspace(0.01, 0.99, 500):
        pred = (y_val_cal >= t).astype(int)
        f1 = f1_score(y_val, pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = t
    
    y_val_ml = (y_val_cal >= best_t).astype(int)
    
    y_test_cal = iso.transform(model.predict_proba(X_test)[:, 1])
    y_test_ml = (y_test_cal >= best_t).astype(int)

    # Get aggressive agent rule predictions
    rule_val = aggressive_agent_rules(val_df)
    rule_test = aggressive_agent_rules(test_df)
    
    # Try different rule risk thresholds on validation
    best_strategy = "ml"
    best_val_f1 = best_f1
    
    strategies = {
        "ml": y_val_ml,
        "rules_0.3": (rule_val["risk_score"].values >= 0.3).astype(int),
        "rules_0.4": (rule_val["risk_score"].values >= 0.4).astype(int),
        "rules_0.5": (rule_val["risk_score"].values >= 0.5).astype(int),
        "union_0.3": np.maximum(y_val_ml, (rule_val["risk_score"].values >= 0.3).astype(int)),
        "union_0.4": np.maximum(y_val_ml, (rule_val["risk_score"].values >= 0.4).astype(int)),
        "union_0.5": np.maximum(y_val_ml, (rule_val["risk_score"].values >= 0.5).astype(int)),
        "intersect_0.3": y_val_ml * (rule_val["risk_score"].values >= 0.3).astype(int),
    }
    
    for name, preds in strategies.items():
        f1 = f1_score(y_val, preds, zero_division=0)
        if f1 > best_val_f1:
            best_val_f1 = f1
            best_strategy = name
    
    # Apply best strategy to test
    if best_strategy == "ml":
        y_test_pred = y_test_ml
    elif best_strategy.startswith("rules_"):
        thresh = float(best_strategy.split("_")[1])
        y_test_pred = (rule_test["risk_score"].values >= thresh).astype(int)
    elif best_strategy.startswith("union_"):
        thresh = float(best_strategy.split("_")[1])
        y_test_pred = np.maximum(y_test_ml, (rule_test["risk_score"].values >= thresh).astype(int))
    elif best_strategy.startswith("intersect_"):
        thresh = float(best_strategy.split("_")[1])
        y_test_pred = y_test_ml * (rule_test["risk_score"].values >= thresh).astype(int)
    else:
        y_test_pred = y_test_ml
    
    return y_test_pred, y_test_cal
