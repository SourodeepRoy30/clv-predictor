import streamlit as st

st.set_page_config(page_title="CLV Predictor", page_icon=":material/insights:", layout="wide")

# Pages grouped by what a visitor wants to do. The files stay in pages/; this list controls the sidebar.
pages = {
    "Start here": [
        st.Page("pages/0_Home.py", title="Home", icon=":material/home:", default=True),
        st.Page("pages/7_Glossary.py", title="Glossary", icon=":material/menu_book:", url_path="glossary"),
    ],
    "Customers": [
        st.Page("pages/1_Customer_Lookup.py", title="Customer Lookup", icon=":material/person_search:",
                url_path="customer-lookup"),
        st.Page("pages/4_At_Risk_Customers.py", title="At-Risk Customers", icon=":material/notification_important:",
                url_path="at-risk-customers"),
        st.Page("pages/2_What_If_Simulator.py", title="What-If Simulator", icon=":material/tune:",
                url_path="what-if-simulator"),
    ],
    "Explore": [
        st.Page("pages/3_Segment_Explorer.py", title="Segment Explorer", icon=":material/donut_large:",
                url_path="segment-explorer"),
        st.Page("pages/5_Product_Insights.py", title="Product Insights", icon=":material/inventory_2:",
                url_path="product-insights"),
    ],
    "About the models": [
        st.Page("pages/6_Model_Info.py", title="Model Info", icon=":material/fact_check:", url_path="model-info"),
    ],
}

st.navigation(pages).run()
