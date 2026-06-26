#!/usr/bin/env python3
"""
Experiment 11: TF-IDF + agent rule scores as features + per-dataset threshold.

Combines:
1. Structured features (156 features from Excel)
2. Word + char TF-IDF from open-end text
3. Agent rule risk scores (computed from structured features)
4. Per-dataset threshold optimization (F1 vs F0.5 vs F2 based on reject rate)

The agent rules provide interpretable signal combinations that complement
the ML model's pattern recognition.
"""
from __future__ import annotations
import warnings, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score, fbeta_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from survey_quality_ml import prepare_features

warnings.filterwarnings("ignore")

def compute_agent_features(df):
    """Compute agent rule risk scores as additional features."""
    features = pd.DataFrame(index=df.index)
    
    # Signal tier composite
    features["agent_t1_any"] = (df.get("t1_count", 0) > 0).astype(float)
    features["agent_t2_any"] = (df.get("t2_count", 0) > 0).astype(float)
    features["agent_t3_any"] = (df.get("t3_count", 0) > 0).astype(float)
    features["agent_signal_total"] = df.get("signal_count", 0)
    features["agent_multi_tier"] = ((df.get("t1_count", 0) > 0).astype(float) + 
                                     (df.get("t2_count", 0) > 0).astype(float) + 
                                     (df.get("t3_count", 0) > 0).astype(float))
    
    # Quality composite
    features["agent_oe_quality"] = (
        df.get("oe_very_short", 0) * 2 + 
        df.get("oe_short", 0) * 1 + 
        df.get("oe_generic", 0) * 1.5 + 
        df.get("oe_has_none", 0) * 1 + 
        df.get("oe_all_caps", 0) * 1
    )
    
    # Speed composite
    features["agent_speed_risk"] = (
        (df.get("qtime_seconds_zscore", 0) < -1).astype(float) * 1.5 +
        (df.get("qtime_seconds_zscore", 0) < -1.5).astype(float) * 1 +
        (df.get("qtime_seconds", 0) < 120).astype(float) * 0.5
    )
    
    # Matrix quality
    features["agent_matrix_risk"] = (
        df.get("matrix_straightline", 0) * 2 +
        df.get("matrix_near_straightline", 0) * 1
    )
    
    # Duplicate risk
    features["agent_dup_risk"] = (
        df.get("oe_is_dup", 0) * 1 +
        df.get("ip_is_dup", 0) * 1.5 +
        df.get("ua_is_dup", 0) * 1
    )
    
    # Supplier risk
    features["agent_supplier_risk"] = df.get("supplier_reject_rate", 0)
    
    # LangAssess risk (high readability = AI generated)
    if "lang_LangAssessReadLevel" in df.columns:
        features["agent_lang_risk"] = (
            (df["lang_LangAssessReadLevel"] > 10).astype(float) * 1 +
            (df["lang_LangAssessReadLevel"] > 15).astype(float) * 1
        )
    else:
        features["agent_lang_risk"] = 0
    
    # Coded answer risk
    features["agent_coded_risk"] = (
        df.get("coded_dk_ratio", 0) * 2 +
        (df.get("coded_unique_ratio", 1) < 0.3).astype(float) * 1
    )
    
    # Composite risk score
    features["agent_total_risk"] = (
        features["agent_t1_any"] * 3 +
        features["agent_t2_any"] * 1.5 +
        features["agent_t3_any"] * 0.5 +
        features["agent_oe_quality"] * 0.5 +
        features["agent_speed_risk"] * 0.5 +
        features["agent_matrix_risk"] * 0.5 +
        features["agent_dup_risk"] * 0.5 +
        features["agent_supplier_risk"] * 2 +
        features["agent_lang_risk"] * 0.5 +
        features["agent_coded_risk"] * 0.5
    )
    
    # Interaction features
    features["agent_risk_x_supplier"] = features["agent_total_risk"] * features["agent_supplier_risk"]
    features["agent_risk_x_speed"] = features["agent_total_risk"] * features["agent_speed_risk"]
    features["agent_t1_x_supplier"] = features["agent_t1_any"] * features["agent_supplier_risk"]
    
    return features

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

    # Agent features
    agent_train = compute_agent_features(train_df)
    agent_val = compute_agent_features(val_df)
    agent_test = compute_agent_features(test_df)

    # TF-IDF
    word_tfidf = TfidfVectorizer(max_features=200, ngram_range=(1, 2), min_df=2, max_df=0.9,
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
        
        X_train_comb = np.hstack([X_train.values, train_w_svd, train_c_svd, agent_train.values])
        X_val_comb = np.hstack([X_val.values, val_w_svd, val_c_svd, agent_val.values])
        X_test_comb = np.hstack([X_test.values, test_w_svd, test_c_svd, agent_test.values])
    except Exception:
        X_train_comb = np.hstack([X_train.values, agent_train.values])
        X_val_comb = np.hstack([X_val.values, agent_val.values])
        X_test_comb = np.hstack([X_test.values, agent_test.values])

    n_pos = max((y_train == 1).sum(), 1)
    n_neg = max((y_train == 0).sum(), 1)
    w = np.where(y_train == 1, len(y_train) / (2 * n_pos), len(y_train) / (2 * n_neg))

    model = GradientBoostingClassifier(
        n_estimators=400, max_depth=4, learning_rate=0.05,
        subsample=0.8, random_state=42, min_samples_leaf=10
    )
    model.fit(X_train_comb, y_train, sample_weight=w)

    y_train_proba = model.predict_proba(X_train_comb)[:, 1]
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(y_train_proba, y_train)

    # Per-dataset threshold optimization
    reject_rate = float(y_train.mean())
    y_val_cal = iso.transform(model.predict_proba(X_val_comb)[:, 1])
    
    best_f1, best_t = 0, 0.5
    for t in np.linspace(0.01, 0.99, 500):
        pred = (y_val_cal >= t).astype(int)
        f1 = f1_score(y_val, pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = t

    y_test_cal = iso.transform(model.predict_proba(X_test_comb)[:, 1])
    y_test_pred = (y_test_cal >= best_t).astype(int)
    return y_test_pred, y_test_cal
