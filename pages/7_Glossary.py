import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from definitions import GLOSSARY, GROUP_ORDER

st.title("Glossary")
st.write(
    "Plain-language definitions of the terms used in this app. The same definitions appear as tooltips "
    "(the ⓘ icons) next to numbers and controls throughout the app."
)

query = st.text_input("Search terms", placeholder="For example: churn, lift, value at risk")
q = query.strip().lower()

matches = {term: entry for term, entry in GLOSSARY.items()
           if not q or q in term.lower() or q in entry["long"].lower()}

if not matches:
    st.info("No terms match your search.")

for group in GROUP_ORDER:
    group_terms = [(term, entry) for term, entry in matches.items() if entry["group"] == group]
    if not group_terms:
        continue
    st.subheader(group)
    for term, entry in group_terms:
        st.markdown(f"**{term}**  \n{entry['long']}")
