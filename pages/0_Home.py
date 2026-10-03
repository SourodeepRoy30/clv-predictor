import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import (load_data, load_models, load_configs, predict_clv, by_customer_id,
                       FEATURE_COLS, SEGMENT_COLORS)
from definitions import tip
from ui import interesting_customers, customer_story, show_story, churn_gauge, DEFAULT_CUSTOMER

data = load_data()
models = load_models()
configs = load_configs()
clusters = by_customer_id(data["clusters"])
modeling_table = by_customer_id(data["modeling_table"])

# ---------------------------------------------------------------
# Hero
# ---------------------------------------------------------------
st.title("CLV Predictor")
st.markdown("##### :gray[Which customers are worth keeping, which are about to leave, and what do they buy?]")

top_segments = ["Elite Wholesalers", "High-Value Regulars"]
is_top = clusters["Segment_Name"].isin(top_segments)
top_customer_share = is_top.mean()
top_revenue_share = clusters.loc[is_top, "Monetary"].sum() / clusters["Monetary"].sum()
lapsed_share = (clusters["Segment_Name"] == "At-Risk/Lapsed").mean()

left, right = st.columns([2, 3], gap="large")
with left:
    st.write(
        "Not all customers are worth the same. This app predicts, for every customer of a UK online gift "
        "retailer, **whether they will buy again** and **how much they are likely to spend**, so a retention "
        "budget goes where it matters most."
    )
    k1, k2 = st.columns(2)
    k1.metric("Customers bringing in", f"{top_revenue_share:.0%} of revenue",
              f"just {top_customer_share:.1%} of customers", delta_color="off",
              help="Elite Wholesalers and High-Value Regulars, by spend during the 18 months to June 2011.")
    k2.metric("Customers who have gone quiet", f"{lapsed_share:.0%}", "At-Risk/Lapsed segment",
              delta_color="off", help=tip("At-Risk/Lapsed"))

with right:
    # Each segment's share of customers vs its share of revenue, as two 100% bars
    seg = clusters.groupby("Segment_Name").agg(Customers=("Monetary", "size"), Revenue=("Monetary", "sum"))
    seg = (seg / seg.sum()).reset_index().melt(id_vars="Segment_Name", var_name="Measure", value_name="Share")
    order = ["Elite Wholesalers", "High-Value Regulars", "Typical Steady", "At-Risk/Lapsed"]
    fig = px.bar(seg, x="Share", y="Measure", color="Segment_Name", orientation="h",
                 color_discrete_map=SEGMENT_COLORS, category_orders={"Segment_Name": order,
                                                                     "Measure": ["Revenue", "Customers"]},
                 text=seg["Share"].map(lambda v: f"{v:.0%}" if v >= 0.05 else ""))
    fig.update_layout(height=230, barmode="stack", margin=dict(l=0, r=0, t=30, b=0),
                      title=dict(text="Share of customers vs share of revenue, by segment", font=dict(size=14)),
                      legend=dict(orientation="h", y=-0.25, title_text=""),
                      xaxis=dict(tickformat=".0%", title=None), yaxis=dict(title=None))
    fig.update_traces(hovertemplate="%{fullData.name}: %{x:.1%}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------
# Try it
# ---------------------------------------------------------------
st.subheader("See it in action")
showcase = interesting_customers(set(modeling_table.index))
labels = {cid: f"{cid}: {reason}" for cid, reason in showcase.items()}
default_index = list(showcase).index(DEFAULT_CUSTOMER) if DEFAULT_CUSTOMER in showcase else 0

with st.container(border=True):
    pick = st.radio("Pick a customer", list(showcase), index=default_index,
                    format_func=lambda cid: labels[cid], horizontal=True)
    features = modeling_table.loc[pick]
    pred = predict_clv(models, configs, "6mo", modeling_table.loc[[pick], FEATURE_COLS]).iloc[0]
    segment = clusters["Segment_Name"].get(pick, "Unassigned")

    g, story = st.columns([1, 2], vertical_alignment="center")
    with g:
        st.plotly_chart(churn_gauge(pred["Churn_Prob"], "6-month churn risk"), use_container_width=True)
    with story:
        tone, text = customer_story(pick, features, pred, segment)
        show_story(tone, text)
        c1, c2 = st.columns(2)
        c1.metric("Expected value, next 6 months", f"£{pred['Expected_CLV']:,.0f}", help=tip("Expected CLV"))
        c2.metric("Value at risk", f"£{pred['Value_At_Risk']:,.0f}", help=tip("Value at risk"))
        if st.button("Open full customer profile", icon=":material/arrow_forward:"):
            st.session_state["lookup_customer"] = int(pick)
            st.switch_page("pages/1_Customer_Lookup.py")

st.divider()

# ---------------------------------------------------------------
# How it works
# ---------------------------------------------------------------
st.subheader("How it works")
STEPS = [
    (":material/receipt_long:", "Transactions", "About a million purchases, December 2009 to December 2011."),
    (":material/cleaning_services:", "Cleaning", "Duplicates, non-product entries and cancelled orders removed."),
    (":material/model_training:", "Models", "A churn model and a spend model, combined into one prediction."),
    (":material/dashboard:", "This app", "Explore the results by customer, segment and product."),
]
for col, (icon, name, text) in zip(st.columns(4), STEPS):
    with col.container(border=True, height="stretch"):
        st.markdown(f"### {icon}")
        st.markdown(f"**{name}**")
        st.caption(text)

st.divider()

# ---------------------------------------------------------------
# What you can do
# ---------------------------------------------------------------
st.subheader("Explore")
FEATURES = [
    ("pages/1_Customer_Lookup.py", ":material/person_search:", "How is this customer doing?",
     "Churn risk, expected value and segment for any customer.", "Customer Lookup"),
    ("pages/4_At_Risk_Customers.py", ":material/notification_important:", "Who should we contact first?",
     "A retention list ranked by revenue at risk, with campaign costs.", "At-Risk Customers"),
    ("pages/2_What_If_Simulator.py", ":material/tune:", "What makes a customer valuable?",
     "Change a customer's behaviour and watch the predictions move.", "What-If Simulator"),
    ("pages/3_Segment_Explorer.py", ":material/donut_large:", "What kinds of customers are there?",
     "Four segments, from elite wholesalers to lapsed customers.", "Segment Explorer"),
    ("pages/5_Product_Insights.py", ":material/inventory_2:", "What sells, when, and with what?",
     "Top products, seasonality, and what is bought together.", "Product Insights"),
    ("pages/6_Model_Info.py", ":material/fact_check:", "Can these predictions be trusted?",
     "How the models were built, tested, and where their limits are.", "Model Info"),
]
for row_start in range(0, len(FEATURES), 3):
    for col, (path, icon, question, text, name) in zip(st.columns(3), FEATURES[row_start:row_start + 3]):
        with col.container(border=True, height="stretch"):
            st.markdown(f"**{question}**")
            st.caption(text)
            st.page_link(path, label=name, icon=icon)

st.caption(
    "Unfamiliar term? Hover over any :material/help_outline: icon, or see the Glossary. "
    "Prefer light or dark? Use the menu at the top right, then Settings. "
    "Data: Online Retail II, UCI Machine Learning Repository."
)
