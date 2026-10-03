import streamlit as st
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import (load_models, load_configs, CHURN_LABEL_THRESHOLD, predict_clv,
                       predict_segment, describe_config)

st.title("What If Simulator")
st.write("Adjust the sliders to simulate a hypothetical customer and see live predictions.")

models = load_models()
configs = load_configs()


def churn_metric(col, label, churn_prob):
    """Show a churn probability with a 'Likely to Churn' / 'Likely Active' label."""
    likely_churn = churn_prob >= CHURN_LABEL_THRESHOLD
    col.metric(
        label,
        f"{churn_prob:.1%}",
        "Likely to Churn" if likely_churn else "Likely Active",
        delta_color="inverse" if likely_churn else "normal"
    )


col_inputs, col_results = st.columns([1, 1])

with col_inputs:
    st.subheader("Customer Behavior")
    recency = st.slider("Recency (days since last purchase)", 0, 400, 60)
    frequency = st.slider("Frequency (number of orders)", 1, 100, 5)
    monetary = st.slider("Monetary (total spend, £)", 0, 20000, 1000, step=50)
    tenure = st.slider("Tenure (days since first purchase)", 0, 555, 200)
    unique_products = st.slider("Unique Products Purchased", 1, 300, 15)

# Derived features, computed the same way as in 3_feature_engineering.ipynb
simulated_customer = pd.DataFrame([{
    'Recency': recency,
    'Frequency': frequency,
    'Monetary': monetary,
    'AOV': monetary / frequency,
    'Tenure': tenure,
    'Unique_Products': unique_products,
    'Avg_Days_Between_Purchases': tenure / frequency
}])

pred_6mo = predict_clv(models, configs, "6mo", simulated_customer).iloc[0]
pred_12mo = predict_clv(models, configs, "12mo", simulated_customer).iloc[0]
segment = predict_segment(models, configs, simulated_customer)[0]

with col_results:
    st.subheader("6-Month Predictions")
    churn_metric(st, "6-Month Churn Risk", pred_6mo["Churn_Prob"])
    st.metric("6-Month Expected CLV", f"£{pred_6mo['Expected_CLV']:,.2f}")
    st.metric("Predicted Segment", segment)
    st.caption(
        f"Spend if they buy again: £{pred_6mo['Spend_If_Retained']:,.2f}; "
        f"value at risk from churn: £{pred_6mo['Value_At_Risk']:,.2f}. "
        f"Model: {describe_config(configs['clv_6mo'])}."
    )

st.divider()
st.subheader("12-Month Outlook")
st.caption(
    "The 12-month model was trained on 12 months of customer history, while the 6-month model used 18 months. "
    "The same inputs are fed to both, so the two outlooks are best compared in direction rather than size."
)

col4, col5 = st.columns(2)
churn_metric(col4, "12-Month Churn Risk", pred_12mo["Churn_Prob"])
col5.metric("12-Month Expected CLV", f"£{pred_12mo['Expected_CLV']:,.2f}")
st.caption(
    f"Spend if they buy again: £{pred_12mo['Spend_If_Retained']:,.2f}; "
    f"value at risk from churn: £{pred_12mo['Value_At_Risk']:,.2f}. "
    f"Model: {describe_config(configs['clv_12mo'])}."
)

if tenure > 365:
    st.warning(
        "Tenure above 365 days is outside what the 12-month model saw in training (its customers had at most "
        "one year of history), so its prediction here is an extrapolation and less reliable."
    )

st.divider()
st.subheader("Computed Feature Values")
st.dataframe(simulated_customer)
