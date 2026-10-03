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
            with st.popover("How to use", icon=":material/help:", width="stretch"):
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


def customer_story(label, features, prediction, segment, horizon_months=6):
    """A plain-English reading of one customer's numbers. Returns (tone, markdown)."""
    tone, headline = churn_tone(prediction["Churn_Prob"])
    recency = int(features["Recency"])
    when = "over a year ago" if recency > 365 else f"{recency} days ago"
    orders = int(features["Frequency"])
    intro = f"They are in the **{segment}** segment and have spent" if segment else "They have spent"
    text = (
        f"**{label} {headline}** ({prediction['Churn_Prob']:.0%} churn risk). "
        f"{intro} £{features['Monetary']:,.0f} over {orders} order{'s' if orders != 1 else ''}, most recently {when}. "
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
    fig.update_layout(height=height, margin=dict(l=35, r=45, t=40, b=0))
    return fig


def value_split_chart(prediction, height=110):
    """
    One horizontal bar showing spend if retained split into expected value (kept) and value at risk.
    This is the Expected Value rule made visible: the two parts always add up to the whole bar.
    """
    fig = go.Figure()
    for name, value, color in [("Expected value", prediction["Expected_CLV"], "#3C9D5D"),
                               ("At risk", prediction["Value_At_Risk"], "#D9534F")]:
        fig.add_trace(go.Bar(
            x=[value], y=[""], orientation="h", name=name, marker_color=color,
            text=f"{name}: £{value:,.0f}", textposition="inside", insidetextanchor="middle",
            hovertemplate=f"{name}: £{value:,.2f}<extra></extra>",
        ))
    fig.update_layout(barmode="stack", height=height, showlegend=False, margin=dict(l=0, r=0, t=28, b=0),
                      title=dict(text=f"If they buy again: £{prediction['Spend_If_Retained']:,.0f}",
                                 font=dict(size=13)),
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def prediction_panel(prediction, horizon_label, help_text):
    """Gauge, value metrics and the kept-versus-at-risk bar for one horizon."""
    gauge_col, numbers_col = st.columns([1, 2], vertical_alignment="center")
    with gauge_col:
        st.plotly_chart(churn_gauge(prediction["Churn_Prob"], f"{horizon_label} churn risk"), width="stretch")
    with numbers_col:
        m1, m2 = st.columns(2)
        m1.metric(f"Expected value, {horizon_label.lower()}", f"£{prediction['Expected_CLV']:,.0f}",
                  help=help_text["Expected CLV"], border=True)
        m2.metric("Value at risk", f"£{prediction['Value_At_Risk']:,.0f}",
                  help=help_text["Value at risk"], border=True)
        if prediction["Spend_If_Retained"] >= 1:
            st.plotly_chart(value_split_chart(prediction), width="stretch")
        else:
            st.caption("Predicted spend if they buy again is very low (a linear prediction below £0, shown as £0), "
                       "so there is little value at risk.")


# Streamlit's built-in colour names, matched to each segment's chart colour
SEGMENT_BADGE_COLORS = {
    "Typical Steady": "blue",
    "High-Value Regulars": "green",
    "At-Risk/Lapsed": "red",
    "Elite Wholesalers": "violet",
}


def segment_badge(segment):
    """A coloured label for a segment name, matching its colour in the charts."""
    return f":{SEGMENT_BADGE_COLORS.get(segment, 'gray')}-badge[{segment}]"
