#!/usr/bin/env python3
"""
Experiment 16: Post-signal agent analysis text as TF-IDF features.

For each respondent, generate a text description of their quality signals
based on the agent analysis rules. This text captures the COMBINATION of
signals in a way that TF-IDF can distinguish.

Example: "fast_completion short_oe high_readability supplier_risk straightline"
vs "normal_speed long_oe low_readability good_supplier diverse_answers"

This is the autoresearch methodology applied to the post-signal agent analysis:
the agent generates a text description, and we use ML on that text.
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
from train_v14_per_dataset_best import get_tfidf_features, train_gbm
from train_v15_raw_excel import extract_raw_excel_features

warnings.filterwarnings("ignore")

def generate_agent_description(df):
    """Generate a text description of each respondent's quality signals."""
    descriptions = []
    for _, row in df.iterrows():
        parts = []
        
        # Timing
        qt_z = row.get("qtime_seconds_zscore", 0)
        if qt_z < -2: parts.append("extreme_speed")
        elif qt_z < -1: parts.append("fast_completion")
        elif qt_z > 2: parts.append("very_slow")
        else: parts.append("normal_speed")
        
        # Open-end
        if row.get("oe_very_short", 0) == 1: parts.append("very_short_oe")
        elif row.get("oe_short", 0) == 1: parts.append("short_oe")
        else: parts.append("adequate_oe")
        
        if row.get("oe_generic", 0) == 1: parts.append("generic_oe")
        if row.get("oe_has_none", 0) == 1: parts.append("none_oe")
        if row.get("oe_all_caps", 0) == 1: parts.append("caps_oe")
        
        oe_chars = row.get("oe_total_chars", 0)
        if oe_chars > 200: parts.append("detailed_oe")
        elif oe_chars > 50: parts.append("moderate_oe")
        
        # Matrix
        if row.get("matrix_straightline", 0) == 1: parts.append("straightline")
        elif row.get("matrix_near_straightline", 0) == 1: parts.append("near_straightline")
        else: parts.append("diverse_matrix")
        
        # Signals
        t1 = row.get("t1_count", 0)
        t2 = row.get("t2_count", 0)
        t3 = row.get("t3_count", 0)
        if t1 > 0: parts.append(f"t1_signal_{t1}")
        if t2 > 0: parts.append(f"t2_signal_{t2}")
        if t3 > 0: parts.append(f"t3_signal_{t3}")
        
        sig_count = row.get("signal_count", 0)
        if sig_count >= 5: parts.append("many_signals")
        elif sig_count >= 3: parts.append("some_signals")
        else: parts.append("few_signals")
        
        # Supplier
        sr = row.get("supplier_reject_rate", 0)
        if sr > 0.3: parts.append("high_risk_supplier")
        elif sr > 0.1: parts.append("medium_risk_supplier")
        else: parts.append("low_risk_supplier")
        
        # LangAssess
        if "lang_LangAssessReadLevel" in row:
            lr = row["lang_LangAssessReadLevel"]
            if lr > 15: parts.append("very_high_readability")
            elif lr > 10: parts.append("high_readability")
            elif lr > 5: parts.append("normal_readability")
            else: parts.append("low_readability")
        
        # Duplicates
        if row.get("oe_is_dup", 0) == 1: parts.append("oe_duplicate")
        if row.get("ip_is_dup", 0) == 1: parts.append("ip_duplicate")
        if row.get("ua_is_dup", 0) == 1: parts.append("ua_duplicate")
        
        # Coded answers
        if row.get("coded_dk_ratio", 0) > 0.3: parts.append("many_dk_answers")
        if row.get("coded_unique_ratio", 1) < 0.3: parts.append("low_coded_diversity")
        
        # Raw features
        if "raw_matrix_q_sl_count" in row:
            if row["raw_matrix_q_sl_count"] > 2: parts.append("multi_q_straightline")
        if "raw_oe_len_cv" in row:
            if row["raw_oe_len_cv"] > 1.5: parts.append("oe_length_inconsistent")
        if "raw_answer_entropy" in row:
            if row["raw_answer_entropy"] < 1.0: parts.append("low_answer_entropy")
        
        descriptions.append(" ".join(parts))
    
    return descriptions


def train_and_predict(train_df, val_df, test_df):
    train_text = train_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in train_df.columns else [""] * len(train_df)
    val_text = val_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in val_df.columns else [""] * len(val_df)
    test_text = test_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in test_df.columns else [""] * len(test_df)

    # Add raw Excel features first
    dataset_name = train_df["dataset"].iloc[0] if "dataset" in train_df.columns else ""
    raw_train = extract_raw_excel_features(dataset_name, train_df["respondent_id"].values)
    raw_val = extract_raw_excel_features(dataset_name, val_df["respondent_id"].values)
    raw_test = extract_raw_excel_features(dataset_name, test_df["respondent_id"].values)
    
    for d, raw in [(train_df, raw_train), (val_df, raw_val), (test_df, raw_test)]:
        if len(raw) > 0:
            raw_indexed = raw.set_index("respondent_id")
            for col in raw_indexed.columns:
                d[f"raw_{col}"] = d["respondent_id"].map(raw_indexed[col]).fillna(0)

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

    # Agent description text
    agent_train_text = generate_agent_description(train_df)
    agent_val_text = generate_agent_description(val_df)
    agent_test_text = generate_agent_description(test_df)

    # Deep features
    deep_train = extract_deep_features(train_df)
    deep_val = extract_deep_features(val_df)
    deep_test = extract_deep_features(test_df)

    # TF-IDF on open-end text
    tfidf_oe = get_tfidf_features(train_text, val_text, test_text, word=True, char=True)
    
    # TF-IDF on agent descriptions
    agent_tfidf = TfidfVectorizer(max_features=100, ngram_range=(1, 1), min_df=1, max_df=0.95,
                                   sublinear_tf=True, binary=True)
    try:
        agent_tfidf.fit(agent_train_text)
        train_agent = agent_tfidf.transform(agent_train_text).toarray()
        val_agent = agent_tfidf.transform(agent_val_text).toarray()
        test_agent = agent_tfidf.transform(agent_test_text).toarray()
    except Exception:
        train_agent = val_agent = test_agent = None

    # Try multiple approaches
    configs = [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.03, "min_samples_leaf": 15},
        {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.08, "min_samples_leaf": 5},
    ]

    approaches = []

    # Build feature sets
    feature_sets = []
    
    # Set 1: Structured + raw
    feature_sets.append(("struct_raw", X_train.values, X_val.values, X_test.values))
    
    # Set 2: + TF-IDF oe
    if tfidf_oe[0] is not None:
        feature_sets.append(("tfidf_oe", 
            np.hstack([X_train.values, tfidf_oe[0]]),
            np.hstack([X_val.values, tfidf_oe[1]]),
            np.hstack([X_test.values, tfidf_oe[2]])))
    
    # Set 3: + agent TF-IDF
    if train_agent is not None:
        feature_sets.append(("agent_tfidf",
            np.hstack([X_train.values, train_agent]),
            np.hstack([X_val.values, val_agent]),
            np.hstack([X_test.values, test_agent])))
    
    # Set 4: + TF-IDF oe + agent TF-IDF
    if tfidf_oe[0] is not None and train_agent is not None:
        feature_sets.append(("oe_agent_tfidf",
            np.hstack([X_train.values, tfidf_oe[0], train_agent]),
            np.hstack([X_val.values, tfidf_oe[1], val_agent]),
            np.hstack([X_test.values, tfidf_oe[2], test_agent])))
    
    # Set 5: + deep + TF-IDF oe + agent
    if tfidf_oe[0] is not None and train_agent is not None:
        feature_sets.append(("deep_oe_agent",
            np.hstack([X_train.values, tfidf_oe[0], train_agent, deep_train.values]),
            np.hstack([X_val.values, tfidf_oe[1], val_agent, deep_val.values]),
            np.hstack([X_test.values, tfidf_oe[2], test_agent, deep_test.values])))

    for name, X_tr, X_va, X_te in feature_sets:
        for cfg in configs:
            m, iso, t, f1 = train_gbm(X_tr, y_train, X_va, y_val, cfg)
            approaches.append((name, m, iso, t, f1, X_tr, X_va, X_te))

    # Pick best
    best = max(approaches, key=lambda a: a[4])
    name, model, iso, best_t, best_f1, _, _, X_te = best

    y_test_cal = iso.transform(model.predict_proba(X_te)[:, 1])
    y_test_pred = (y_test_cal >= best_t).astype(int)
    return y_test_pred, y_test_cal
