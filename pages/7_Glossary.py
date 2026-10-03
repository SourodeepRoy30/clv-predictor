import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import load_data
from definitions import GLOSSARY, GROUP_ORDER
from ui import page_header, snapshot_timeline, expected_value_demo, lift_example

page_header("Glossary", "What do these terms mean?")

# ---------------------------------------------------------------
# Key ideas, illustrated
# ---------------------------------------------------------------
st.subheader("Key ideas, illustrated")
st.page_link("pages/6_Model_Info.py", label="How a prediction is made, step by step: see Model Info",
             icon=":material/account_tree:")

tab_time, tab_value, tab_lift = st.tabs(["Snapshot and churn", "Expected value", "Lift and confidence"])

with tab_time:
    st.markdown("Every prediction looks at a customer's **history up to a snapshot date**, then predicts what "
                "happens in the **prediction window** after it. A customer who buys nothing in that window has "
                "**churned**.")
    model = st.segmented_control("Model", list(["6-month model", "12-month model"]), default="6-month model",
                                 key="timeline_model") or "6-month model"
    st.plotly_chart(snapshot_timeline(model), width="stretch", config={"displayModeBar": False},
                    key="timeline_chart")
    st.caption("Illustrative customers. Hover over a purchase or a window for details. Switch models to see "
               "Customer B change from churned to returned: a longer window gives customers more time to come back, "
               "which is why the 12-month churn rate is lower.")

with tab_value:
    st.markdown("**Spend if retained** is split by the chance the customer returns. The part expected to arrive is "
                "the **expected value**; the rest is **value at risk**. Move the sliders to see how they trade off.")
    expected_value_demo("glossary_ev")

with tab_lift:
    st.markdown("**Confidence** and **lift** describe how strongly two products are bought together. "
                "Here they are worked through for real product pairs from the data.")
    lift_example(load_data()["association_rules"], "glossary_lift")

st.divider()

# ---------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------
st.subheader("Definitions")
st.caption("The same definitions appear when you hover over the :material/help_outline: icons throughout the app.")

c1, c2 = st.columns([2, 3], vertical_alignment="bottom")
query = c1.text_input("Search", placeholder="For example: churn, lift, value at risk",
                      label_visibility="collapsed")
group = c2.segmented_control("Topic", ["All"] + GROUP_ORDER, default="All", key="glossary_group",
                             label_visibility="collapsed") or "All"

q = query.strip().lower()
matches = [(term, entry) for term, entry in GLOSSARY.items()
           if (group == "All" or entry["group"] == group)
           and (not q or q in term.lower() or q in entry["long"].lower())]

if not matches:
    st.info("No terms match. Try another word or choose All.", icon=":material/search_off:")

for g in GROUP_ORDER:
    terms = [(t, e) for t, e in matches if e["group"] == g]
    if not terms:
        continue
    st.markdown(f"#### {g}")
    for row_start in range(0, len(terms), 2):
        for col, (term, entry) in zip(st.columns(2), terms[row_start:row_start + 2]):
            with col.container(border=True, height="stretch"):
                st.markdown(f"**{term}**")
                st.write(entry["long"])
