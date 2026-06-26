#!/usr/bin/env python3
"""
Experiment 18: Cross-dataset transfer learning.

Train a base model on ALL 11 datasets combined, then fine-tune on the
per-dataset training split. The base model learns general quality patterns
that transfer across datasets. The fine-tuning adapts to the specific
dataset's reject rate and patterns.

Also: use the base model's predictions as an additional feature for the
per-dataset model. This is a form of stacking where the base model provides
a "prior" on the rejection probability.
"""
from __future__ import annotations
import warnings, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import sys, pickle
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from survey_quality_ml import prepare_features, ANNOTATED_DIR, DATASET_MAP, load_signal_map, extract_features_from_excel, add_supplier_risk
from train_v13_deep import extract_deep_features
from train_v14_per_dataset_best import get_tfidf_features, train_gbm
from train_v15_raw_excel import extract_raw_excel_features
from train_v16_agent_text import generate_agent_description

warnings.filterwarnings("ignore")

# Cache for base model
_base_model_cache = None
_base_tfidf_cache = None

def get_base_model():
    """Train a base model on all datasets combined."""
    global _base_model_cache, _base_tfidf_cache
    if _base_model_cache is not None:
        return _base_model_cache, _base_tfidf_cache
    
    signal_map = load_signal_map()
    all_dfs = []
    for fname in sorted(DATASET_MAP.keys()):
        fp = ANNOTATED_DIR / fname
        if not fp.exists(): continue
        df, _ = extract_features_from_excel(fp, signal_map)
        if df is not None and len(df) > 0 and "label" in df.columns:
            # Add raw features
            raw = extract_raw_excel_features(fname, df["respondent_id"].values)
            if len(raw) > 0:
                raw_indexed = raw.set_index("respondent_id")
                for col in raw_indexed.columns:
                    df[f"raw_{col}"] = df["respondent_id"].map(raw_indexed[col]).fillna(0)
            all_dfs.append(df)
    
    combined = pd.concat(all_dfs, ignore_index=True)
    
    # Add supplier risk using global stats
    combined["supplier_reject_rate"] = combined.groupby("supplier_name")["label"].transform('mean')
    combined["supplier_reject_rate"] = combined["supplier_reject_rate"].fillna(combined["label"].mean())
    combined["supplier_x_signals"] = combined["supplier_reject_rate"] * combined["signal_count"]
    combined["supplier_x_t1"] = combined["supplier_reject_rate"] * combined["t1_count"]
    combined["supplier_x_t2"] = combined["supplier_reject_rate"] * combined["t2_count"]
    combined["signals_x_matrix"] = combined["signal_count"] * (1 - combined["matrix_unique_ratio"])
    
    # Add deep features
    deep = extract_deep_features(combined)
    for col in deep.columns:
        combined[f"deep_{col}"] = deep[col]
    
    # TF-IDF on all text
    all_text = combined["_oe_raw_text"].fillna("").values
    word_tfidf = TfidfVectorizer(max_features=200, ngram_range=(1, 2), min_df=2, max_df=0.9,
                                  stop_words='english', sublinear_tf=True)
    char_tfidf = TfidfVectorizer(max_features=200, ngram_range=(2, 4), min_df=2, max_df=0.9,
                                  analyzer='char_wb', sublinear_tf=True)
    word_tfidf.fit(all_text)
    char_tfidf.fit(all_text)
    
    train_w = word_tfidf.transform(all_text)
    train_c = char_tfidf.transform(all_text)
    n_w = min(50, train_w.shape[1], train_w.shape[0] - 1)
    n_c = min(50, train_c.shape[1], train_c.shape[0] - 1)
    svd_w = TruncatedSVD(n_components=n_w, random_state=42)
    svd_c = TruncatedSVD(n_components=n_c, random_state=42)
    train_w_svd = svd_w.fit_transform(train_w)
    train_c_svd = svd_c.fit_transform(train_c)
    
    X, y = prepare_features(combined)
    X_comb = np.hstack([X.values, train_w_svd, train_c_svd])
    
    n_pos = max((y == 1).sum(), 1)
    n_neg = max((y == 0).sum(), 1)
    w_arr = np.where(y == 1, len(y) / (2 * n_pos), len(y) / (2 * n_neg))
    
    base_model = GradientBoostingClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, random_state=42, min_samples_leaf=20
    )
    base_model.fit(X_comb, y, sample_weight=w_arr)
    
    _base_model_cache = (base_model, word_tfidf, char_tfidf, svd_w, svd_c)
    _base_tfidf_cache = (word_tfidf, char_tfidf, svd_w, svd_c)
    
    return _base_model_cache, _base_tfidf_cache


def train_and_predict(train_df, val_df, test_df):
    train_text = train_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in train_df.columns else [""] * len(train_df)
    val_text = val_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in val_df.columns else [""] * len(val_df)
    test_text = test_df["_oe_raw_text"].fillna("").values if "_oe_raw_text" in test_df.columns else [""] * len(test_df)

    # Add raw Excel features
    dataset_name = train_df["dataset"].iloc[0] if "dataset" in train_df.columns else ""
    raw_train = extract_raw_excel_features(dataset_name, train_df["respondent_id"].values)
    raw_val = extract_raw_excel_features(dataset_name, val_df["respondent_id"].values)
    raw_test = extract_raw_excel_features(dataset_name, test_df["respondent_id"].values)
    
    for d, raw in [(train_df, raw_train), (val_df, raw_val), (test_df, raw_test)]:
        if len(raw) > 0:
            raw_indexed = raw.set_index("respondent_id")
            for col in raw_indexed.columns:
                d[f"raw_{col}"] = d["respondent_id"].map(raw_indexed[col]).fillna(0)

    # Get base model predictions as features
    (base_model, word_tfidf, char_tfidf, svd_w, svd_c), _ = get_base_model()
    
    # Prepare features for base model
    def get_base_features(df, text):
        X, _ = prepare_features(df)
        # Add deep features
        deep = extract_deep_features(df)
        for col in deep.columns:
            df_copy = df.copy()
            df_copy[f"deep_{col}"] = deep[col]
        X_deep, _ = prepare_features(df)
        
        w = word_tfidf.transform(text)
        c = char_tfidf.transform(text)
        w_svd = svd_w.transform(w)
        c_svd = svd_c.transform(c)
        return np.hstack([X_deep.values, w_svd, c_svd])
    
    try:
        base_train_proba = base_model.predict_proba(get_base_features(train_df, train_text))[:, 1]
        base_val_proba = base_model.predict_proba(get_base_features(val_df, val_text))[:, 1]
        base_test_proba = base_model.predict_proba(get_base_features(test_df, test_text))[:, 1]
    except Exception:
        base_train_proba = np.zeros(len(train_df))
        base_val_proba = np.zeros(len(val_df))
        base_test_proba = np.zeros(len(test_df))

    # Add base model predictions as features
    train_df = train_df.copy()
    val_df = val_df.copy()
    test_df = test_df.copy()
    train_df["base_model_proba"] = base_train_proba
    val_df["base_model_proba"] = base_val_proba
    test_df["base_model_proba"] = base_test_proba

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
    tfidf_oe = get_tfidf_features(train_text, val_text, test_text, word=True, char=True)
    
    # Agent description TF-IDF
    agent_train_text = generate_agent_description(train_df)
    agent_val_text = generate_agent_description(val_df)
    agent_test_text = generate_agent_description(test_df)
    
    agent_tfidf = TfidfVectorizer(max_features=100, ngram_range=(1, 1), min_df=1, max_df=0.95,
                                   sublinear_tf=True, binary=True)
    try:
        agent_tfidf.fit(agent_train_text)
        train_agent = agent_tfidf.transform(agent_train_text).toarray()
        val_agent = agent_tfidf.transform(agent_val_text).toarray()
        test_agent = agent_tfidf.transform(agent_test_text).toarray()
    except Exception:
        train_agent = val_agent = test_agent = None

    # Build feature sets
    feature_sets = []
    
    def add_set(name, extra_train, extra_val, extra_test):
        if extra_train is not None:
            feature_sets.append((name,
                np.hstack([X_train.values, extra_train]),
                np.hstack([X_val.values, extra_val]),
                np.hstack([X_test.values, extra_test])))
        else:
            feature_sets.append((name, X_train.values, X_val.values, X_test.values))
    
    add_set("struct_base", None, None, None)
    if tfidf_oe[0] is not None:
        add_set("struct_tfidf_base", tfidf_oe[0], tfidf_oe[1], tfidf_oe[2])
    if train_agent is not None:
        add_set("struct_agent_base", train_agent, val_agent, test_agent)
    if tfidf_oe[0] is not None and train_agent is not None:
        add_set("all_base", np.hstack([tfidf_oe[0], train_agent, deep_train.values]),
                np.hstack([tfidf_oe[1], val_agent, deep_val.values]),
                np.hstack([tfidf_oe[2], test_agent, deep_test.values]))

    configs = [
        {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 10},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.03, "min_samples_leaf": 15},
        {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.08, "min_samples_leaf": 5},
    ]

    approaches = []
    for name, X_tr, X_va, X_te in feature_sets:
        for cfg in configs:
            m, iso, t, f1 = train_gbm(X_tr, y_train, X_va, y_val, cfg)
            approaches.append((name, m, iso, t, f1, X_tr, X_va, X_te))

    best = max(approaches, key=lambda a: a[4])
    name, model, iso, best_t, best_f1, _, _, X_te = best

    y_test_cal = iso.transform(model.predict_proba(X_te)[:, 1])
    y_test_pred = (y_test_cal >= best_t).astype(int)
    return y_test_pred, y_test_cal
