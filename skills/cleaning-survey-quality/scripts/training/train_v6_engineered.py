#!/usr/bin/env python3
"""
Experiment 6: Feature engineering + agent rules as features.

Create new interaction features and use agent rule determinations
as additional ML features. The agent rules provide signal combinations
that the ML model might not discover on its own.
"""
from __future__ import annotations
import warnings, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from survey_quality_ml import prepare_features
from predict_quality import apply_agent_rules

warnings.filterwarnings("ignore")

def add_engineered_features(df):
    """Add new features derived from existing ones."""
    # Timing x open-end interaction (fast + short = worse)
    if "qtime_seconds" in df.columns and "oe_total_chars" in df.columns:
        df["fast_short_oe"] = (df["qtime_seconds"] < df["qtime_seconds"].median()).astype(float) * \
                              (df["oe_total_chars"] < df["oe_total_chars"].median()).astype(float)
    
    # Matrix straightline x signal count (straightline + many signals = worse)
    if "matrix_unique_ratio" in df.columns and "signal_count" in df.columns:
        df["straightline_x_signals"] = (1 - df["matrix_unique_ratio"]) * df["signal_count"]
    
    # LangAssess x open-end length (high readability + short = AI generated)
    if "lang_LangAssessReadLevel" in df.columns and "oe_mean_chars" in df.columns:
        df["high_read_short"] = (df["lang_LangAssessReadLevel"] > df["lang_LangAssessReadLevel"].median()).astype(float) * \
                                (df["oe_mean_chars"] < df["oe_mean_chars"].median()).astype(float)
    
    # Supplier risk x matrix straightline
    if "supplier_reject_rate" in df.columns and "matrix_unique_ratio" in df.columns:
        df["supplier_x_straightline"] = df["supplier_reject_rate"] * (1 - df["matrix_unique_ratio"])
    
    # Multiple signal tier combination
    if "t1_count" in df.columns and "t2_count" in df.columns and "t3_count" in df.columns:
        df["any_tier_signal"] = ((df["t1_count"] + df["t2_count"] + df["t3_count"]) > 0).astype(float)
        df["multi_tier_signal"] = ((df["t1_count"] > 0).astype(float) + 
                                    (df["t2_count"] > 0).astype(float) + 
                                    (df["t3_count"] > 0).astype(float))
    
    # Duplicate cluster score
    dup_cols = [c for c in df.columns if c.endswith("_is_dup")]
    if dup_cols:
        df["dup_cluster_score"] = df[dup_cols].sum(axis=1)
    
    # Open-end quality composite
    oe_cols = [c for c in ["oe_very_short", "oe_short", "oe_generic", "oe_has_none", "oe_all_caps"] if c in df.columns]
    if oe_cols:
        df["oe_quality_score"] = df[oe_cols].sum(axis=1)
    
    return df

def train_and_predict(train_df, val_df, test_df):
    # Add agent rule features
    rule_train = apply_agent_rules(train_df, {}, {})
    rule_val = apply_agent_rules(val_df, {}, {})
    rule_test = apply_agent_rules(test_df, {}, {})
    
    train_df = train_df.copy()
    val_df = val_df.copy()
    test_df = test_df.copy()
    
    train_df["rule_risk"] = rule_train["rule_risk_score"].values
    val_df["rule_risk"] = rule_val["rule_risk_score"].values
    test_df["rule_risk"] = rule_test["rule_risk_score"].values
    train_df["rule_has_signal"] = (rule_train["rule_determination"] != "KEEP").astype(int).values
    val_df["rule_has_signal"] = (rule_val["rule_determination"] != "KEEP").astype(int).values
    test_df["rule_has_signal"] = (rule_test["rule_determination"] != "KEEP").astype(int).values

    # Add engineered features
    train_df = add_engineered_features(train_df)
    val_df = add_engineered_features(val_df)
    test_df = add_engineered_features(test_df)

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
        n_estimators=400, max_depth=4, learning_rate=0.05,
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
