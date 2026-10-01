import os
import json

import joblib
import numpy as np
import pandas as pd
import streamlit as st

# Paths are resolved relative to this file, so the app works whichever folder it is launched from
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")

# Feature columns, in the exact order every model expects
FEATURE_COLS = ['Recency', 'Frequency', 'Monetary', 'AOV', 'Tenure', 'Unique_Products', 'Avg_Days_Between_Purchases']

# A churn probability at or above this is labelled "Likely to Churn" (more likely than not to churn).
# It is a display label only: CLV predictions use the rule in each configuration file, not this value.
CHURN_LABEL_THRESHOLD = 0.5

# One colour per segment, shared by every page
SEGMENT_COLORS = {
    'Typical Steady': '#4C78A8',
    'High-Value Regulars': '#54A24B',
    'At-Risk/Lapsed': '#E45756',
    'Elite Wholesalers': '#B279A2'
}


def _model_file(path_from_config):
    """The notebooks store paths relative to notebooks/ (e.g. ../models/x.pkl); resolve them inside models/."""
    return os.path.join(MODELS_DIR, os.path.basename(path_from_config))


@st.cache_data
def load_configs():
    """
    Load the configuration files written by the notebooks: how each CLV horizon produces a prediction
    (5_regression.ipynb, 7_clv_12month.ipynb) and which cluster number is which segment (6_clustering.ipynb).
    Reading these instead of hardcoding them keeps the app in step with the notebooks whenever they are rerun.
    """
    def read(name):
        with open(os.path.join(MODELS_DIR, name)) as f:
            return json.load(f)

    return {
        "clv_6mo": read("clv_6mo_config.json"),
        "clv_12mo": read("clv_12mo_config.json"),
        "segment_names": {int(k): v for k, v in read("segment_names.json").items()},
    }


@st.cache_resource
def load_models():
    """
    Load all trained model artifacts once, cached across the entire app session.
    st.cache_resource is used (not st.cache_data) since these are model objects, not plain data.
    """
    configs = load_configs()
    return {
        "churn_6mo": joblib.load(os.path.join(MODELS_DIR, "churn_model.pkl")),
        "churn_12mo": joblib.load(os.path.join(MODELS_DIR, "churn_model_12mo.pkl")),
        "clv_6mo": joblib.load(_model_file(configs["clv_6mo"]["model_path"])),
        "clv_12mo": joblib.load(_model_file(configs["clv_12mo"]["model_path"])),
        "kmeans_model": joblib.load(os.path.join(MODELS_DIR, "kmeans_model.pkl")),
        "scaler_rfm": joblib.load(os.path.join(MODELS_DIR, "scaler_rfm.pkl")),
    }


@st.cache_data
def load_data():
    """
    Load all reference data tables once, cached across the entire app session.
    st.cache_data is used (not st.cache_resource) since these are plain dataframes.
    """
    return {
        "modeling_table": pd.read_csv(os.path.join(DATA_DIR, "modeling_table.csv"), index_col=0),
        "modeling_table_12mo": pd.read_csv(os.path.join(DATA_DIR, "modeling_table_12mo.csv"), index_col=0),
        "rfm_table": pd.read_csv(os.path.join(DATA_DIR, "rfm_table.csv"), index_col=0),
        "clusters": pd.read_csv(os.path.join(DATA_DIR, "customer_clusters.csv"), index_col=0),
        "association_rules": pd.read_csv(os.path.join(DATA_DIR, "association_rules.csv")),
        "product_summary": pd.read_csv(os.path.join(DATA_DIR, "product_summary.csv")),
    }


def by_customer_id(df):
    """Return a copy indexed by integer Customer ID, whether the ID is a column or the index."""
    df = df.copy()
    if 'Customer ID' in df.columns:
        df = df.set_index('Customer ID')
    df.index = df.index.astype(int)
    df.index.name = 'Customer ID'
    return df


def predict_clv(models, configs, horizon, X):
    """
    Predict CLV for one horizon ("6mo" or "12mo") exactly as the configuration file describes.

    Returns one row per customer:
      Churn_Prob         probability of no purchase in the horizon (Stage 1)
      Spend_If_Retained  predicted spend if the customer does buy again (Stage 2)
      Expected_CLV       the CLV prediction; under the Expected Value rule, (1 - Churn_Prob) x Spend_If_Retained
      Value_At_Risk      Spend_If_Retained - Expected_CLV, the revenue expected to be lost to churn
    """
    config = configs[f"clv_{horizon}"]
    X = X[FEATURE_COLS]

    churn_prob = models[f"churn_{horizon}"].predict_proba(X)[:, 1]
    raw = models[f"clv_{horizon}"].predict(X)
    amount = np.clip(np.expm1(raw) if config.get("log_target") else raw, 0, None)

    if config["family"] == "Two-Stage":
        spend_if_retained = amount
        if config["rule"] == "Expected Value":
            expected = (1 - churn_prob) * spend_if_retained
        else:
            expected = np.where(churn_prob >= config["threshold"], 0, spend_if_retained)
        value_at_risk = spend_if_retained - expected
    else:
        # A single-stage model predicts CLV directly, so there is no separate "spend if retained"
        spend_if_retained = np.full(len(X), np.nan)
        expected = amount
        value_at_risk = np.full(len(X), np.nan)

    return pd.DataFrame({
        "Churn_Prob": churn_prob,
        "Spend_If_Retained": spend_if_retained,
        "Expected_CLV": expected,
        "Value_At_Risk": value_at_risk,
    }, index=X.index)


def predict_segment(models, configs, X):
    """Assign segments with the saved K-Means model and the saved cluster-number-to-name mapping."""
    scaled = models["scaler_rfm"].transform(X[['Recency', 'Frequency', 'Monetary']])
    return [configs["segment_names"][int(c)] for c in models["kmeans_model"].predict(scaled)]


def describe_config(config):
    """One-line, human-readable description of how a horizon's CLV prediction is produced."""
    if config["family"] == "Two-Stage":
        rule = config["rule"] if config["rule"] == "Expected Value" else f"Hard Cutoff at {config['threshold']:.2f}"
        return f"two-stage model ({rule} rule, Stage 2: {config['model']})"
    return f"single-stage model ({config['model']})"
