import streamlit as st
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import load_models, load_data, load_configs, FEATURE_COLS, predict_clv, predict_segment, by_customer_id
from definitions import GLOSSARY, tip
from ui import page_header, interesting_customers, customer_story, show_story, prediction_panel, DEFAULT_CUSTOMER

page_header(
    "Customer Lookup",
    "How is this customer doing?",
    how_to="""
**What this page shows:** for one customer, how likely they are to stop buying, how much they are expected to spend, and how much of that is at risk.

**How to use it:** choose a customer from the list (type to search by ID), or click one of the examples.

**How to read it:**
- The coloured box sums the customer up in one sentence: red means likely to stop buying, amber uncertain, green likely to keep buying.
- The gauge shows churn risk: the chance they make no purchase in the period.
- The bar splits what they would spend if they buy again into the part expected to arrive (green) and the part at risk (red).
- The two tabs show the 6-month and 12-month outlooks. The 12-month model uses an earlier snapshot of the customer, so the two are not directly comparable.
""",
)

models = load_models()
configs = load_configs()
data = load_data()
modeling_table = by_customer_id(data["modeling_table"])
modeling_table_12mo = by_customer_id(data["modeling_table_12mo"])
clusters = by_customer_id(data["clusters"])

customer_ids = sorted(modeling_table.index.tolist())
showcase = interesting_customers(set(customer_ids))

# Initial selection: the customer chosen on the Home page if there is one, otherwise a telling example
if "lookup_customer" in st.session_state:
    st.session_state["lookup_id"] = st.session_state.pop("lookup_customer")
if st.session_state.get("lookup_id") not in customer_ids:
    st.session_state["lookup_id"] = DEFAULT_CUSTOMER if DEFAULT_CUSTOMER in customer_ids else customer_ids[0]


def use_example():
    """Copy the clicked example into the customer selector."""
    chosen = st.session_state.get("lookup_example")
    if chosen is not None:
        st.session_state["lookup_id"] = chosen


pick_col, _ = st.columns([1, 2])
customer_id = pick_col.selectbox("Customer ID", customer_ids, key="lookup_id")
st.pills("Or try an example", list(showcase), format_func=lambda cid: showcase[cid],
         key="lookup_example", on_change=use_example)

features = modeling_table.loc[customer_id]
X_6mo = modeling_table.loc[[customer_id], FEATURE_COLS]
pred_6mo = predict_clv(models, configs, "6mo", X_6mo).iloc[0]
segment = clusters["Segment_Name"].get(customer_id) or predict_segment(models, configs, X_6mo)[0]

tone, text = customer_story(f"Customer {customer_id}", features, pred_6mo, segment)
show_story(tone, text)

help_text = {term: tip(term) for term in ["Expected CLV", "Value at risk"]}
tab_6, tab_12, tab_details = st.tabs(["Next 6 months", "Next 12 months", "Customer details"])

with tab_6:
    st.caption("Behaviour up to 2011-06-08, predicting spend from 2011-06-09 to 2011-12-09.")
    prediction_panel(pred_6mo, "6-month", help_text)

with tab_12:
    if customer_id in modeling_table_12mo.index:
        pred_12mo = predict_clv(models, configs, "12mo", modeling_table_12mo.loc[[customer_id], FEATURE_COLS]).iloc[0]
        st.caption("Behaviour up to 2010-11-30, predicting spend from 2010-12-01 to 2011-12-09. "
                   "This earlier snapshot is why the two outlooks can differ.")
        prediction_panel(pred_12mo, "12-month", help_text)
    else:
        st.info("This customer's first purchase was after 2010-11-30, so the 12-month model, which needs history "
                "up to that date, cannot score them.", icon=":material/info:")

with tab_details:
    s1, s2 = st.columns(2)
    s1.metric("Segment", segment, help=GLOSSARY.get(segment, {}).get("short", tip("Segment")), border=True)
    s2.metric("Historical spend", f"£{features['Monetary']:,.0f}", help=tip("Monetary"), border=True)

    labels = {"Recency": "Days since last purchase", "Frequency": "Orders", "Monetary": "Total spend (£)",
              "AOV": "Average order value (£)", "Tenure": "Days since first purchase",
              "Unique_Products": "Different products bought",
              "Avg_Days_Between_Purchases": "Average days between orders"}
    snapshots = {"6-month model (as of 2011-06-08)": modeling_table.loc[customer_id, FEATURE_COLS]}
    if customer_id in modeling_table_12mo.index:
        snapshots["12-month model (as of 2010-11-30)"] = modeling_table_12mo.loc[customer_id, FEATURE_COLS]
    details = pd.DataFrame(snapshots).rename(index=labels)
    st.dataframe(details.style.format("{:,.2f}"), width="stretch")
    st.caption("The features each model sees for this customer. See the Glossary for definitions.")
