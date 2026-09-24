import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import load_models, load_data, FEATURE_COLS, THRESHOLD_6MO, THRESHOLD_12MO, SEGMENT_NAMES

st.set_page_config(page_title="Customer Lookup", page_icon="🔍", layout="wide")
st.title("Customer Lookup")
st.write("Enter a Customer ID to see their churn risk, predicted lifetime value, and segment.")

models = load_models()
data = load_data()

modeling_table = data["modeling_table"]
customer_ids = sorted(modeling_table.index.tolist())

customer_id = st.selectbox("Select a Customer ID", customer_ids)

if customer_id:
    customer_row = modeling_table.loc[[customer_id], FEATURE_COLS]

    st.subheader(f"Results for Customer {int(customer_id)}")

    col1, col2, col3 = st.columns(3)

    st.divider()
    st.subheader("12-Month Outlook")
    st.caption(
    "Note: the 6-month and 12-month models use different churn definitions and decision "
    "thresholds (15% vs 11%), so their risk percentages are not directly comparable in "
    "magnitude, only whether each individually exceeds its own threshold."
    )

    modeling_table_12mo = data["modeling_table_12mo"]
    
    if customer_id in modeling_table_12mo.index:
        customer_row_12mo = modeling_table_12mo.loc[[customer_id], FEATURE_COLS]

        col4, col5 = st.columns(2)

        churn_proba_12mo = models["churn_model_12mo"].predict_proba(customer_row_12mo)[0, 1]
        is_at_risk_12mo = churn_proba_12mo >= THRESHOLD_12MO
        churn_label_12mo = "Likely to Churn" if is_at_risk_12mo else "Likely Active"
        col4.metric(
            "12-Month Churn Risk",
            f"{churn_proba_12mo*100:.1f}%",
            churn_label_12mo,
            delta_color="inverse" if is_at_risk_12mo else "normal"
        )

        predicted_amount_12mo = max(0, models["stage2_model_12mo"].predict(customer_row_12mo)[0])
        final_clv_12mo = 0 if is_at_risk_12mo else predicted_amount_12mo
        col5.metric("12-Month Predicted CLV", f"£{final_clv_12mo:,.2f}")
    else:
        st.info(
            "This customer does not have sufficient calibration history for the 12-month model "
            "(the 12-month model uses a different calibration window and customer set than the 6-month model)."
        )

    # Churn risk, 6-month 
    churn_proba_6mo = models["churn_model_6mo"].predict_proba(customer_row)[0, 1]
    is_at_risk_6mo = churn_proba_6mo >= THRESHOLD_6MO
    churn_label_6mo = "Likely to Churn" if is_at_risk_6mo else "Likely Active"
    col1.metric(
        "6-Month Churn Risk",
        f"{churn_proba_6mo*100:.1f}%",
        churn_label_6mo,
        delta_color="inverse" if is_at_risk_6mo else "normal"
    )

    # Predicted CLV, 6-month, two-stage
    predicted_amount_6mo = max(0, models["stage2_model_6mo"].predict(customer_row)[0])
    final_clv_6mo = 0 if churn_proba_6mo >= THRESHOLD_6MO else predicted_amount_6mo
    col2.metric("6-Month Predicted CLV", f"£{final_clv_6mo:,.2f}")

    # Segment
    rfm_features = customer_row[['Recency', 'Frequency', 'Monetary']]
    rfm_scaled = models["scaler_rfm"].transform(rfm_features)
    segment_id = models["kmeans_model"].predict(rfm_scaled)[0]
    segment_name = SEGMENT_NAMES[segment_id]
    col3.metric("Customer Segment", segment_name)

    st.divider()
    st.subheader("Raw Customer Features")
    st.dataframe(customer_row)