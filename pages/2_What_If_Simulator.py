import streamlit as st
import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import load_models, THRESHOLD_6MO, THRESHOLD_12MO, SEGMENT_NAMES

st.set_page_config(page_title="What If Simulator", page_icon="🎛️", layout="wide")
st.title("What If Simulator")
st.write("Adjust the sliders to simulate a hypothetical customer and see live predictions.")

models = load_models()

col_inputs, col_results = st.columns([1, 1])

with col_inputs:
    st.subheader("Customer Behavior")
    recency = st.slider("Recency (days since last purchase)", 0, 400, 60)
    frequency = st.slider("Frequency (number of orders)", 1, 100, 5)
    monetary = st.slider("Monetary (total spend, £)", 0, 20000, 1000, step=50)
    tenure = st.slider("Tenure (days since first purchase)", 0, 555, 200)
    unique_products = st.slider("Unique Products Purchased", 1, 300, 15)

# Derived features, computed the same way as in 3_feature_engineering.ipynb
aov = monetary / frequency
avg_days_between_purchases = tenure / frequency

simulated_customer = pd.DataFrame([{
    'Recency': recency,
    'Frequency': frequency,
    'Monetary': monetary,
    'AOV': aov,
    'Tenure': tenure,
    'Unique_Products': unique_products,
    'Avg_Days_Between_Purchases': avg_days_between_purchases
}])

with col_results:
    st.subheader("Predictions")

    churn_proba = models["churn_model_6mo"].predict_proba(simulated_customer)[0, 1]
    is_at_risk = churn_proba >= THRESHOLD_6MO
    churn_label = "Likely to Churn" if is_at_risk else "Likely Active"
    st.metric(
        "6-Month Churn Risk",
        f"{churn_proba*100:.1f}%",
        churn_label,
        delta_color="inverse" if is_at_risk else "normal"
    )

    predicted_amount = max(0, models["stage2_model_6mo"].predict(simulated_customer)[0])
    final_clv = 0 if is_at_risk else predicted_amount
    st.metric("6-Month Predicted CLV", f"£{final_clv:,.2f}")

    rfm_features = simulated_customer[['Recency', 'Frequency', 'Monetary']]
    rfm_scaled = models["scaler_rfm"].transform(rfm_features)
    segment_id = models["kmeans_model"].predict(rfm_scaled)[0]
    st.metric("Predicted Segment", SEGMENT_NAMES[segment_id])

st.divider()
st.subheader("12-Month Outlook")
st.caption(
    "Note: the 6-month and 12-month models use different churn definitions and decision "
    "thresholds (15% vs 11%), so their risk percentages are not directly comparable in "
    "magnitude, only whether each individually exceeds its own threshold."
)

col4, col5, col6 = st.columns(3)

churn_proba_12mo = models["churn_model_12mo"].predict_proba(simulated_customer)[0, 1]
is_at_risk_12mo = churn_proba_12mo >= THRESHOLD_12MO
churn_label_12mo = "Likely to Churn" if is_at_risk_12mo else "Likely Active"
col4.metric(
    "12-Month Churn Risk",
    f"{churn_proba_12mo*100:.1f}%",
    churn_label_12mo,
    delta_color="inverse" if is_at_risk_12mo else "normal"
)

predicted_amount_12mo = max(0, models["stage2_model_12mo"].predict(simulated_customer)[0])
final_clv_12mo = 0 if is_at_risk_12mo else predicted_amount_12mo
col5.metric("12-Month Predicted CLV", f"£{final_clv_12mo:,.2f}")

col6.metric("Predicted Segment", SEGMENT_NAMES[segment_id])
st.divider()
st.subheader("Computed Feature Values")
st.dataframe(simulated_customer)