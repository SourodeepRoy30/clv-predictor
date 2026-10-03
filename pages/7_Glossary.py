import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from definitions import GLOSSARY, GROUP_ORDER
from ui import page_header

page_header("Glossary", "What do these terms mean?")
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
    st.subheader(g)
    for row_start in range(0, len(terms), 2):
        for col, (term, entry) in zip(st.columns(2), terms[row_start:row_start + 2]):
            with col.container(border=True, height="stretch"):
                st.markdown(f"**{term}**")
                st.write(entry["long"])
