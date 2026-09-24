import streamlit as st
import pandas as pd
import joblib

@st.cache_resource
def load_models():
    """
    Load all trained model artifacts once, cached across the entire app session.
    st.cache_resource is used (not st.cache_data) since these are model objects,
    not plain data, this avoids re-loading .pkl files from disk on every page interaction.
    """
    return {
        "churn_model_6mo": joblib.load("models/churn_model.pkl"),
        "stage2_model_6mo": joblib.load("models/stage2_regressor.pkl"),
        "churn_model_12mo": joblib.load("models/churn_model_12mo.pkl"),
        "stage2_model_12mo": joblib.load("models/stage2_regressor_12mo.pkl"),
        "kmeans_model": joblib.load("models/kmeans_model.pkl"),
        "scaler_rfm": joblib.load("models/scaler_rfm.pkl"),
    }

@st.cache_data
def load_data():
    """
    Load all reference data tables once, cached across the entire app session.
    st.cache_data is used (not st.cache_resource) since these are plain dataframes.
    """
    return {
        "modeling_table": pd.read_csv("data/modeling_table.csv", index_col=0),
        "modeling_table_12mo": pd.read_csv("data/modeling_table_12mo.csv", index_col=0),
        "rfm_table": pd.read_csv("data/rfm_table.csv", index_col=0),
        "clusters": pd.read_csv("data/customer_clusters.csv", index_col=0),
        "association_rules": pd.read_csv("data/association_rules.csv"),
        "product_summary": pd.read_csv("data/product_summary.csv"),
    }

# Feature columns, in the exact order every model expects
FEATURE_COLS = ['Recency', 'Frequency', 'Monetary', 'AOV', 'Tenure', 'Unique_Products', 'Avg_Days_Between_Purchases']

# Final decision thresholds established during modeling
THRESHOLD_6MO = 0.15
THRESHOLD_12MO = 0.11

SEGMENT_NAMES = {
    0: 'At-Risk/Lapsed',
    1: 'Typical Steady',
    2: 'Elite Wholesalers',
    3: 'High-Value Regulars'
}