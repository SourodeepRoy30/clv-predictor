import streamlit as st
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import load_models, load_configs, load_data, predict_clv, predict_segment, by_customer_id
from definitions import tip
from ui import page_header, customer_story, show_story, prediction_panel

page_header(
    "What-If Simulator",
    "What makes a customer valuable?",
    how_to="""
**What this page does:** describe a hypothetical customer with the sliders, and see how the models respond.

**How to use it:**
- Start from one of the typical profiles, then move one slider at a time to see what each behaviour changes.
- Average order value and average days between orders are calculated from your inputs, the same way as for real customers.

**Things to try:**
- Raise *days since last purchase* and watch the churn risk climb: recency is the strongest churn signal.
- Raise *total spend* and *orders* together and watch the expected value grow.
""",
)

models = load_models()
configs = load_configs()
data = load_data()
modeling_table = by_customer_id(data["modeling_table"])
clusters = by_customer_id(data["clusters"])

SLIDERS = {
    # key: (label, min, max, step, glossary term)
    "Recency": ("Days since last purchase", 0, 400, 1, "Recency"),
    "Frequency": ("Number of orders", 1, 100, 1, "Frequency"),
    "Monetary": ("Total spend (£)", 0, 20000, 50, "Monetary"),
    "Tenure": ("Days since first purchase", 0, 555, 1, "Tenure"),
    "Unique_Products": ("Different products bought", 1, 300, 1, "Unique products"),
}

# Typical profiles: the median customer of each segment (calculated live), kept within the slider ranges
PROFILE_SEGMENTS = ["Typical Steady", "At-Risk/Lapsed", "High-Value Regulars"]
joined = modeling_table.join(clusters["Segment_Name"])
profiles = {}
for seg in PROFILE_SEGMENTS:
    medians = joined.loc[joined["Segment_Name"] == seg, list(SLIDERS)].median()
    profiles[seg] = {k: int(min(max(round(medians[k] / s[3]) * s[3], s[1]), s[2])) for k, s in SLIDERS.items()}

if "sim_Recency" not in st.session_state:
    for k, v in profiles["Typical Steady"].items():
        st.session_state[f"sim_{k}"] = v


def load_profile():
    """Set every slider to the chosen profile's values."""
    chosen = st.session_state.get("sim_profile")
    if chosen:
        for k, v in profiles[chosen].items():
            st.session_state[f"sim_{k}"] = v


st.pills("Start from a typical customer", PROFILE_SEGMENTS, key="sim_profile", on_change=load_profile,
         help="Sets the sliders to the median customer of that segment.")

inputs_col, results_col = st.columns([2, 3], gap="large")

with inputs_col:
    with st.container(border=True):
        values = {k: st.slider(label, lo, hi, step=step, key=f"sim_{k}", help=tip(term))
                  for k, (label, lo, hi, step, term) in SLIDERS.items()}

# Derived features, computed the same way as in 3_feature_engineering.ipynb
simulated = pd.DataFrame([{
    "Recency": values["Recency"],
    "Frequency": values["Frequency"],
    "Monetary": values["Monetary"],
    "AOV": values["Monetary"] / values["Frequency"],
    "Tenure": values["Tenure"],
    "Unique_Products": values["Unique_Products"],
    "Avg_Days_Between_Purchases": values["Tenure"] / values["Frequency"],
}])

pred_6mo = predict_clv(models, configs, "6mo", simulated).iloc[0]
pred_12mo = predict_clv(models, configs, "12mo", simulated).iloc[0]
segment = predict_segment(models, configs, simulated)[0]
help_text = {term: tip(term) for term in ["Expected CLV", "Value at risk"]}

with results_col:
    tone, text = customer_story("This customer", simulated.iloc[0], pred_6mo, segment)
    show_story(tone, text)

    tab_6, tab_12, tab_features = st.tabs(["Next 6 months", "Next 12 months", "Calculated features"])
    with tab_6:
        prediction_panel(pred_6mo, "6-month", help_text)
    with tab_12:
        if values["Tenure"] > 365:
            st.warning("Days since first purchase is above 365: the 12-month model only saw customers with up to "
                       "a year of history, so this prediction is an extrapolation.", icon=":material/warning:")
        prediction_panel(pred_12mo, "12-month", help_text)
        st.caption("The 12-month model was trained on 12 months of history rather than 18, so compare the two "
                   "outlooks by direction rather than size.")
    with tab_features:
        st.metric("Segment these values fall into", segment, help=tip("Segment"), border=True)
        derived = pd.DataFrame({
            "Value": [f"£{simulated['AOV'][0]:,.2f}", f"{simulated['Avg_Days_Between_Purchases'][0]:,.1f} days"]
        }, index=["Average order value", "Average days between orders"])
        st.dataframe(derived, width="stretch")
        st.caption("Calculated from your inputs: total spend divided by orders, and days since first purchase "
                   "divided by orders.")
