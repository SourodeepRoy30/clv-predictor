"""Shared visual building blocks, so every page looks and reads the same way."""
import plotly.graph_objects as go
import streamlit as st

# Customers worth looking at first, each illustrating something different.
# The reason is shown to the visitor; everything else is calculated live from the data.
INTERESTING_CUSTOMERS = {
    13902: "A big spender who has gone quiet",
    14878: "An active, regular customer",
    14911: "One of five elite wholesalers",
    12346: "Looked like a top customer, until a cancelled order was removed",
}
DEFAULT_CUSTOMER = 13902


def page_header(title, question, how_to=None):
    """Title, the question the page answers, and an optional 'How to use' popover."""
    left, right = st.columns([5, 1], vertical_alignment="bottom")
    with left:
        st.title(title)
        st.markdown(f"##### :gray[{question}]")
    if how_to:
        with right:
            with st.popover("How to use", icon=":material/help:", use_container_width=True):
                st.markdown(how_to)


def interesting_customers(available_ids):
    """The showcase customers present in the data, with a fallback if none are."""
    shown = {cid: reason for cid, reason in INTERESTING_CUSTOMERS.items() if cid in available_ids}
    if not shown:
        shown = {cid: "Example customer" for cid in list(available_ids)[:3]}
    return shown


def churn_tone(churn_prob):
    """Map a churn probability to a tone and a short headline."""
    if churn_prob >= 0.5:
        return "error", "is likely to stop buying"
    if churn_prob >= 0.3:
        return "warning", "could go either way"
    return "success", "is likely to keep buying"


def customer_story(customer_id, features, prediction, segment, horizon_months=6):
    """A plain-English reading of one customer's numbers. Returns (tone, markdown)."""
    tone, headline = churn_tone(prediction["Churn_Prob"])
    recency = int(features["Recency"])
    when = "over a year ago" if recency > 365 else f"{recency} days ago"
    orders = int(features["Frequency"])
    text = (
        f"**Customer {customer_id} {headline}** ({prediction['Churn_Prob']:.0%} churn risk). "
        f"They are in the **{segment}** segment and have spent £{features['Monetary']:,.0f} "
        f"over {orders} order{'s' if orders != 1 else ''}, most recently {when}. "
    )
    spend = prediction["Spend_If_Retained"]
    if spend >= 1:
        text += (
            f"If they buy again, they would likely spend about £{spend:,.0f} in the next {horizon_months} months, "
            f"so **£{prediction['Value_At_Risk']:,.0f} is at risk**."
        )
    else:
        text += "Even if they return, their predicted spend is very low."
    return tone, text


def show_story(tone, text):
    """Display a customer story in a coloured box matching its tone."""
    icons = {"error": ":material/trending_down:", "warning": ":material/swap_vert:",
             "success": ":material/trending_up:"}
    getattr(st, tone)(text, icon=icons[tone])


def churn_gauge(churn_prob, title="Churn risk", height=190):
    """A compact gauge for a churn probability: green (low) to red (high)."""
    tone, _ = churn_tone(churn_prob)
    bar_color = {"error": "#D9534F", "warning": "#E8A33D", "success": "#3C9D5D"}[tone]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=churn_prob * 100,
        number={"suffix": "%", "valueformat": ".0f"},
        title={"text": title, "font": {"size": 14}},
        gauge={
            "axis": {"range": [0, 100], "ticksuffix": "%", "tickvals": [0, 30, 50, 100]},
            "bar": {"color": bar_color, "thickness": 0.35},
            "steps": [
                {"range": [0, 30], "color": "rgba(60,157,93,0.18)"},
                {"range": [30, 50], "color": "rgba(232,163,61,0.18)"},
                {"range": [50, 100], "color": "rgba(217,83,79,0.18)"},
            ],
        },
    ))
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=40, b=0))
    return fig
