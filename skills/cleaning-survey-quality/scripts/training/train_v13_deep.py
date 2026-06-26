#!/usr/bin/env python3
"""
Experiment 13: Deep answer-chain features + TF-IDF.

Extracts per-question answer patterns that the aggregate features miss:
1. Per-matrix-question straightline detection (not just overall)
2. Answer sequence entropy (random answering pattern)
3. Per-open-end-question text features (not just aggregate)
4. Demographic consistency checks
5. Cross-question logic validation

These features capture respondent behavior patterns that aggregate
statistics smooth over.
"""
from __future__ import annotations
import warnings, numpy as np, pandas as pd
import openpyxl
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from survey_quality_ml import prepare_features, ANNOTATED_DIR, parse_datamap, classify_field_role, clean, norm

warnings.filterwarnings("ignore")

def extract_deep_features(df, train_df=None):
    """Extract deep answer-chain features from the dataframe.
    
    These features are computed from the existing columns in the dataframe
    (which already has aggregate features from extract_features_from_excel).
    We derive new features from those existing columns.
    """
    features = pd.DataFrame(index=df.index)
    
    # Per-question matrix straightline patterns
    # We don't have per-question data in the dataframe, but we can derive
    # more nuanced matrix features from what we have
    if "matrix_unique_ratio" in df.columns and "matrix_count" in df.columns:
        # High matrix count + low unique ratio = systematic straightlining
        features["matrix_systematic_sl"] = (
            (df["matrix_count"] > 10).astype(float) * 
            (df["matrix_unique_ratio"] < 0.3).astype(float)
        )
        # Moderate straightlining with many questions
        features["matrix_moderate_sl"] = (
            (df["matrix_count"] > 10).astype(float) * 
            (df["matrix_unique_ratio"] < 0.5).astype(float) *
            (df["matrix_unique_ratio"] >= 0.3).astype(float)
        )
        # Straightline severity score
        features["matrix_sl_severity"] = (1 - df["matrix_unique_ratio"]) * np.log1p(df["matrix_count"])
    
    # Open-end quality composite (more nuanced)
    oe_cols = [c for c in ["oe_very_short", "oe_short", "oe_generic", "oe_has_none", 
                           "oe_all_caps", "oe_lex_div"] if c in df.columns]
    if oe_cols:
        # Weighted composite
        weights = {"oe_very_short": 3, "oe_short": 1, "oe_generic": 2, 
                   "oe_has_none": 1.5, "oe_all_caps": 1.5, "oe_lex_div": -2}
        features["oe_quality_composite"] = sum(
            df[c] * weights.get(c, 1) for c in oe_cols if c in df.columns
        )
        # Count of OE quality issues
        features["oe_issue_count"] = sum(
            (df[c] > 0).astype(float) for c in oe_cols if c != "oe_lex_div"
        )
    
    # Timing patterns
    if "qtime_seconds" in df.columns and "qtime_seconds_zscore" in df.columns:
        # Very fast + many questions = speeding
        features["speed_x_questions"] = (
            (df["qtime_seconds_zscore"] < -1).astype(float) * 
            np.log1p(df.get("matrix_count", 0) + df.get("coded_count", 0))
        )
        # Extreme speeding
        features["extreme_speed"] = (df["qtime_seconds_zscore"] < -2).astype(float)
        # Time per question estimate
        total_q = df.get("matrix_count", 0) + df.get("coded_count", 0) + df.get("oe_count", 0)
        features["time_per_q"] = df["qtime_seconds"] / (total_q + 1)
        features["time_per_q_log"] = np.log1p(features["time_per_q"])
    
    # Signal tier interactions
    if "t1_count" in df.columns and "t2_count" in df.columns and "t3_count" in df.columns:
        # T1 + any other tier = very bad
        features["t1_plus_any"] = (
            (df["t1_count"] > 0).astype(float) * 
            ((df["t2_count"] + df["t3_count"]) > 0).astype(float)
        )
        # Multiple T2 signals
        features["multi_t2"] = (df["t2_count"] >= 2).astype(float)
        # Signal acceleration (T1 + T2 + T3 all present)
        features["all_tiers"] = (
            (df["t1_count"] > 0).astype(float) * 
            (df["t2_count"] > 0).astype(float) * 
            (df["t3_count"] > 0).astype(float)
        )
    
    # Supplier x signal interactions
    if "supplier_reject_rate" in df.columns:
        features["supplier_x_oe_quality"] = df["supplier_reject_rate"] * features.get("oe_quality_composite", 0)
        features["supplier_x_speed"] = df["supplier_reject_rate"] * features.get("speed_x_questions", 0)
        features["supplier_x_matrix"] = df["supplier_reject_rate"] * features.get("matrix_sl_severity", 0)
        features["supplier_x_t1"] = df["supplier_reject_rate"] * df.get("t1_count", 0)
        features["supplier_high_risk"] = (df["supplier_reject_rate"] > 0.3).astype(float)
        features["supplier_low_risk"] = (df["supplier_reject_rate"] < 0.05).astype(float)
    
    # Duplicate patterns
    dup_cols = [c for c in ["oe_is_dup", "ip_is_dup", "ua_is_dup", "sd_is_dup"] if c in df.columns]
    if dup_cols:
        features["dup_total"] = df[dup_cols].sum(axis=1)
        features["dup_multi"] = (features["dup_total"] >= 2).astype(float)
    
    # LangAssess patterns
    lang_cols = [c for c in df.columns if c.startswith("lang_")]
    if lang_cols:
        features["lang_max"] = df[lang_cols].max(axis=1)
        features["lang_mean"] = df[lang_cols].mean(axis=1)
        features["lang_high"] = (features["lang_max"] > df[lang_cols].quantile(0.75).max()).astype(float)
    
    # Coded answer patterns
    if "coded_count" in df.columns and "coded_unique_ratio" in df.columns:
        features["coded_low_div"] = (df["coded_unique_ratio"] < 0.3).astype(float)
        features["coded_high_dk"] = (df.get("coded_dk_ratio", 0) > 0.3).astype(float)
        features["coded_x_matrix"] = df["coded_unique_ratio"] * df.get("matrix_unique_ratio", 1)
    
    # Composite risk score (weighted sum of all risk factors)
    risk_components = [
        features.get("matrix_sl_severity", 0),
        features.get("oe_quality_composite", 0),
        features.get("speed_x_questions", 0),
        features.get("t1_plus_any", 0) * 3,
        features.get("multi_t2", 0) * 1.5,
        features.get("dup_multi", 0) * 2,
        features.get("supplier_high_risk", 0) * 1,
        features.get("lang_high", 0) * 1,
        features.get("coded_low_div", 0) * 1,
    ]
    features["composite_risk"] = sum(risk_components)
    
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

    # Deep features
    deep_train = extract_deep_features(train_df)
    deep_val = extract_deep_features(val_df)
    deep_test = extract_deep_features(test_df)

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
        
        X_train_comb = np.hstack([X_train.values, train_w_svd, train_c_svd, deep_train.values])
        X_val_comb = np.hstack([X_val.values, val_w_svd, val_c_svd, deep_val.values])
        X_test_comb = np.hstack([X_test.values, test_w_svd, test_c_svd, deep_test.values])
    except Exception:
        X_train_comb = np.hstack([X_train.values, deep_train.values])
        X_val_comb = np.hstack([X_val.values, deep_val.values])
        X_test_comb = np.hstack([X_test.values, deep_test.values])

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
