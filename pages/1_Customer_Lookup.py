import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import (load_models, load_data, load_configs, FEATURE_COLS, CHURN_LABEL_THRESHOLD,
                       predict_clv, predict_segment, by_customer_id, describe_config)

st.set_page_config(page_title="Customer Lookup", page_icon="🔍", layout="wide")
st.title("Customer Lookup")
st.write("Select a Customer ID to see their churn risk, expected lifetime value, and segment.")

models = load_models()
configs = load_configs()
data = load_data()

modeling_table = by_customer_id(data["modeling_table"])
modeling_table_12mo = by_customer_id(data["modeling_table_12mo"])
clusters = by_customer_id(data["clusters"])


def churn_metric(col, label, churn_prob):
    """Show a churn probability with a 'Likely to Churn' / 'Likely Active' label."""
    likely_churn = churn_prob >= CHURN_LABEL_THRESHOLD
    col.metric(
        label,
        f"{churn_prob:.1%}",
        "Likely to Churn" if likely_churn else "Likely Active",
        delta_color="inverse" if likely_churn else "normal"
    )


customer_id = st.selectbox("Select a Customer ID", sorted(modeling_table.index.tolist()))

if customer_id is not None:
    # 6-month outlook
    X_6mo = modeling_table.loc[[customer_id], FEATURE_COLS]
    pred_6mo = predict_clv(models, configs, "6mo", X_6mo).iloc[0]

    segment = clusters["Segment_Name"].get(customer_id)
    if segment is None:
        segment = predict_segment(models, configs, X_6mo)[0]

    st.subheader(f"Customer {customer_id}: 6-Month Outlook")
    st.caption("Based on behaviour up to 2011-06-08, predicting spend from 2011-06-09 to 2011-12-09.")

    col1, col2, col3 = st.columns(3)
    churn_metric(col1, "6-Month Churn Risk", pred_6mo["Churn_Prob"])
    col2.metric("6-Month Expected CLV", f"£{pred_6mo['Expected_CLV']:,.2f}")
    col3.metric("Customer Segment", segment)

    st.caption(
        f"If this customer buys again, they are predicted to spend £{pred_6mo['Spend_If_Retained']:,.2f}. "
        f"Expected CLV weights that by their {1 - pred_6mo['Churn_Prob']:.1%} chance of returning; "
        f"the remaining £{pred_6mo['Value_At_Risk']:,.2f} is the value at risk from churn. "
        f"Model: {describe_config(configs['clv_6mo'])}."
    )

    # 12-month outlook
    st.divider()
    st.subheader("12-Month Outlook")
    st.caption(
        "The 12-month model uses an earlier snapshot: behaviour up to 2010-11-30, predicting spend from "
        "2010-12-01 to 2011-12-09. Its features for this customer therefore differ from the 6-month model's, "
        "and the two predictions are not simple multiples of each other."
    )

    if customer_id in modeling_table_12mo.index:
        X_12mo = modeling_table_12mo.loc[[customer_id], FEATURE_COLS]
        pred_12mo = predict_clv(models, configs, "12mo", X_12mo).iloc[0]

        col4, col5 = st.columns(2)
        churn_metric(col4, "12-Month Churn Risk", pred_12mo["Churn_Prob"])
        col5.metric("12-Month Expected CLV", f"£{pred_12mo['Expected_CLV']:,.2f}")
        st.caption(
            f"Spend if they buy again: £{pred_12mo['Spend_If_Retained']:,.2f}; "
            f"value at risk from churn: £{pred_12mo['Value_At_Risk']:,.2f}. "
            f"Model: {describe_config(configs['clv_12mo'])}."
        )
    else:
        st.info(
            "This customer has no purchases before 2010-12-01, so the 12-month model, which needs "
            "history up to that date, cannot score them."
        )

    # Raw features
    st.divider()
    st.subheader("Customer Features")
    st.write("**6-month model** (as of 2011-06-08)")
    st.dataframe(X_6mo)
    if customer_id in modeling_table_12mo.index:
        st.write("**12-month model** (as of 2010-11-30)")
        st.dataframe(modeling_table_12mo.loc[[customer_id], FEATURE_COLS])
