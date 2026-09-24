import streamlit as st

st.set_page_config(page_title="CLV Predictor", page_icon="📊", layout="wide")

st.title("CLV Predictor")
st.write(
    "An interactive dashboard for customer lifetime value prediction, churn risk, "
    "segmentation, and product insights, built on real e-commerce transaction data."
)
st.write("Use the sidebar to navigate between features.")