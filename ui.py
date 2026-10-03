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


# ---------------------------------------------------------------------------
# Interactive flowchart: how a prediction is made
# ---------------------------------------------------------------------------
import textwrap


def _wrap(text, width=52):
    """Break text into lines for a Plotly hover card (which does not wrap on its own)."""
    return "<br>".join(textwrap.wrap(text, width))


def _theme_colors():
    """Hover-card colours matching the viewer's current light or dark theme."""
    theme = getattr(getattr(st.context, "theme", None), "type", None)
    if theme == "light":
        return {"bg": "#FFFFFF", "font": "#1E2330", "border": "#3A6EA5"}
    return {"bg": "#1A1F2A", "font": "#E6E8EE", "border": "#3A6EA5"}


def _flow_steps(example):
    """Content for each box: label, hover card, and the detail shown when clicked."""
    e = example or {}
    eg = (lambda text: f" For customer {e['id']}: {text}.") if e else (lambda text: "")
    return {
        "history": {
            "title": "Customer history", "sub": "7 measures of past behaviour",
            "box": "<b>Customer history</b> ⓘ<br><span style='font-size:11px'>7 behaviour measures</span>",
            "hover": "Everything the models know about a customer: days since their last order, number of orders, "
                     "total spend, average order value, days since their first order, number of different products, "
                     "and average days between orders." + eg(f"£{e.get('monetary', 0):,.0f} over "
                                                              f"{e.get('orders', 0)} orders"),
            "detail": "The models only see behaviour up to a fixed **snapshot** date (2011-06-08 for the 6-month "
                      "model), and predict what happens after it. Each customer is described by seven measures; "
                      "the Glossary defines each one.",
            "link": ("pages/1_Customer_Lookup.py", "See a customer's history in Customer Lookup"),
            "x": 1.0, "y": 1.0, "fill": "rgba(154,160,172,0.16)", "line": "#9AA0AC",
        },
        "stage1": {
            "title": "Stage 1: Will they buy again?", "sub": "churn risk p",
            "box": "<b>Stage 1</b> ⓘ<br>Will they buy again?<br><span style='font-size:11px'>churn risk p</span>",
            "hover": "A gradient boosting classifier estimates p, the probability that the customer makes no "
                     "purchase in the period." + eg(f"p = {e.get('p', 0):.0%}"),
            "detail": "Stage 1 is a classifier trained on whether each customer bought again. Its output *p* is the "
                      "**churn risk**. It ranks customers correctly about 4 times in 5 (ROC-AUC about 0.83 on "
                      "unseen customers): given one customer who stopped buying and one who did not, it usually "
                      "gives the first the higher risk.",
            "link": ("pages/6_Model_Info.py", "How accurate is it? See Model Info"),
            "x": 3.85, "y": 2.0, "fill": "rgba(58,110,165,0.16)", "line": "#3A6EA5",
        },
        "stage2": {
            "title": "Stage 2: How much, if they do?", "sub": "spend if retained s",
            "box": "<b>Stage 2</b> ⓘ<br>How much, if they do?<br><span style='font-size:11px'>spend if retained s</span>",
            "hover": "A regression model, trained only on customers who did come back, estimates s, how much the "
                     "customer would spend if they buy again." + eg(f"s = £{e.get('s', 0):,.0f}"),
            "detail": "Training Stage 2 only on returning customers means it never has to explain the many "
                      "customers who spend nothing; that is Stage 1's job. Its output *s* is **spend if retained**.",
            "link": ("pages/2_What_If_Simulator.py", "Try changing a customer in the What-If Simulator"),
            "x": 3.85, "y": 0.0, "fill": "rgba(58,110,165,0.16)", "line": "#3A6EA5",
        },
        "combine": {
            "title": "Combine", "sub": "weight s by the chance they return",
            "box": "<b>Combine</b> ⓘ<br><span style='font-size:11px'>split s using p</span>",
            "hover": "The two answers are combined: spend if retained is split by the chance the customer returns "
                     "(1 - p) and the chance they leave (p).",
            "detail": "This is the **expected value rule**. It was chosen over predicting £0 for every customer "
                      "above a churn cut-off because its predictions add up to actual revenue (about 100%, against "
                      "79% for the cut-off), and because it can still rank customers who might leave.",
            "link": ("pages/6_Model_Info.py", "Why this design? See Model Info"),
            "x": 6.6, "y": 1.0, "fill": "rgba(154,160,172,0.16)", "line": "#9AA0AC",
        },
        "ev": {
            "title": "Expected value", "sub": "(1 - p) × s",
            "box": "<b>Expected value</b> ⓘ<br>(1 - p) × s",
            "hover": "The revenue expected from the customer over the period: the app's CLV prediction."
                     + eg(f"(1 - {e.get('p', 0):.2f}) × £{e.get('s', 0):,.0f} = £{e.get('ev', 0):,.0f}"),
            "detail": "**Expected value** (expected CLV) is what the business can expect from the customer as things "
                      "stand. Across many customers these predictions add up to the revenue that actually arrives.",
            "link": ("pages/1_Customer_Lookup.py", "See it for any customer in Customer Lookup"),
            "x": 9.15, "y": 2.0, "fill": "rgba(60,157,93,0.18)", "line": "#3C9D5D",
        },
        "var": {
            "title": "Value at risk", "sub": "p × s",
            "box": "<b>Value at risk</b> ⓘ<br>p × s",
            "hover": "The revenue expected to be lost if nothing is done: the part of spend if retained that churn "
                     "would take away." + eg(f"{e.get('p', 0):.2f} × £{e.get('s', 0):,.0f} = £{e.get('var', 0):,.0f}"),
            "detail": "**Value at risk** is what a retention campaign is trying to save. Ranking customers by it puts "
                      "valuable customers who might leave at the top. Expected value and value at risk always add "
                      "up to spend if retained.",
            "link": ("pages/4_At_Risk_Customers.py", "See the ranked list in At-Risk Customers"),
            "x": 9.15, "y": 0.0, "fill": "rgba(217,83,79,0.18)", "line": "#D9534F",
        },
    }


def prediction_flowchart(key, example=None, height=340, show_details=True):
    """
    The two-stage prediction as a flowchart. Hovering over (or tapping) a box shows a short card;
    clicking a box shows a detailed panel below. A text version is always available in an expander.
    `example` (optional): dict with id, p, s, ev, var, monetary, orders for a worked example.
    """
    steps = _flow_steps(example)
    colors = _theme_colors()
    w, h = 2.0, 1.0
    fig = go.Figure()

    for node_id, s in steps.items():
        x0, x1, y0, y1 = s["x"] - w / 2, s["x"] + w / 2, s["y"] - h / 2, s["y"] + h / 2
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=s["fill"],
                      line=dict(color=s["line"], width=2), layer="below")
        fig.add_annotation(x=s["x"], y=s["y"], showarrow=False, align="center",
                           text=s["box"], font=dict(size=13))
        # A grid of invisible points across the box, so hovering anywhere on it shows the card
        gx = [x0 + w * f for f in (0.1, 0.3, 0.5, 0.7, 0.9)]
        gy = [y0 + h * f for f in (0.2, 0.5, 0.8)]
        pts = [(a, b) for a in gx for b in gy]
        fig.add_trace(go.Scatter(
            x=[p[0] for p in pts], y=[p[1] for p in pts], mode="markers",
            marker=dict(size=28, opacity=0), customdata=[node_id] * len(pts), name="",
            hovertemplate=f"<b>{s['title']}</b><br>{_wrap(s['hover'])}<extra></extra>",
            selected=dict(marker=dict(opacity=0)), unselected=dict(marker=dict(opacity=0)),
        ))

    arrows = [("history", "stage1"), ("history", "stage2"), ("stage1", "combine"),
              ("stage2", "combine"), ("combine", "ev"), ("combine", "var")]
    for a, b in arrows:
        fig.add_annotation(x=steps[b]["x"] - w / 2, y=steps[b]["y"], ax=steps[a]["x"] + w / 2, ay=steps[a]["y"],
                           xref="x", yref="y", axref="x", ayref="y", showarrow=True, text="",
                           arrowhead=2, arrowsize=1.2, arrowwidth=1.6, arrowcolor="#9AA0AC")

    fig.update_layout(
        height=height, showlegend=False, margin=dict(l=0, r=0, t=10, b=0), dragmode=False,
        hovermode="closest", hoverdistance=40,
        hoverlabel=dict(bgcolor=colors["bg"], bordercolor=colors["border"],
                        font=dict(size=13, color=colors["font"]), align="left"),
        xaxis=dict(range=[-0.1, 10.25], visible=False, fixedrange=True),
        yaxis=dict(range=[-0.6, 2.6], visible=False, fixedrange=True),
    )

    config = {"displayModeBar": False}
    if show_details:
        event = st.plotly_chart(fig, key=key, on_select="rerun", selection_mode="points",
                                config=config, width="stretch")
        st.caption("Hover over a step (or tap it on a phone) to see what it does. Click a step for more detail.")
        points = event.selection.points if event and event.selection else []
        if points:
            node = points[0].get("customdata")
            node = node[0] if isinstance(node, (list, tuple)) else node
            if node in steps:
                s = steps[node]
                with st.container(border=True):
                    st.markdown(f"**{s['title']}**")
                    st.markdown(s["detail"])
                    st.page_link(s["link"][0], label=s["link"][1], icon=":material/arrow_forward:")
    else:
        st.plotly_chart(fig, key=key, config=config, width="stretch")
        st.caption("Hover over a step (or tap it on a phone) to see what it does.")

    with st.expander("Read all steps as text"):
        for s in steps.values():
            st.markdown(f"**{s['title']}** ({s['sub']}): {s['hover']}")


def flowchart_example(models, configs, modeling_table, customer_id):
    """Numbers for the flowchart's worked example, for one customer (6-month model)."""
    from app_utils import predict_clv, FEATURE_COLS
    if customer_id not in modeling_table.index:
        return None
    row = modeling_table.loc[customer_id]
    pred = predict_clv(models, configs, "6mo", modeling_table.loc[[customer_id], FEATURE_COLS]).iloc[0]
    return {"id": customer_id, "p": pred["Churn_Prob"], "s": pred["Spend_If_Retained"], "ev": pred["Expected_CLV"],
            "var": pred["Value_At_Risk"], "monetary": row["Monetary"], "orders": int(row["Frequency"])}


# ---------------------------------------------------------------------------
# Illustrations for the Glossary
# ---------------------------------------------------------------------------
import pandas as pd

TIMELINE_WINDOWS = {
    "6-month model": {"history": ("2009-12-01", "2011-06-09"), "prediction": ("2011-06-09", "2011-12-10"),
                      "snapshot": "2011-06-09"},
    "12-month model": {"history": ("2009-12-01", "2010-12-01"), "prediction": ("2010-12-01", "2011-12-10"),
                       "snapshot": "2010-12-01"},
}

# Illustrative customers (not real ones), chosen so each tells a different story
TIMELINE_CUSTOMERS = {
    "Customer A": ["2010-02-15", "2010-09-10", "2011-03-20", "2011-09-25"],
    "Customer B": ["2010-01-20", "2010-06-05", "2011-04-12"],
    "Customer C": ["2011-08-03", "2011-10-30"],
}


def _hover_layout(fig):
    colors = _theme_colors()
    fig.update_layout(hoverlabel=dict(bgcolor=colors["bg"], bordercolor=colors["border"],
                                      font=dict(size=13, color=colors["font"]), align="left"))
    return fig


def snapshot_timeline(model="6-month model"):
    """Timeline showing the history window, the snapshot, the prediction window, and what that means for three customers."""
    w = TIMELINE_WINDOWS[model]
    snap = pd.Timestamp(w["snapshot"])
    pred_end = pd.Timestamp(w["prediction"][1])
    fig = go.Figure()
    rows = ["What the model sees"] + list(TIMELINE_CUSTOMERS)

    # The two windows, as hoverable bars on the top row
    for name, (start, end), color, text in [
        ("History", w["history"], "rgba(58,110,165,0.55)",
         "The customer's behaviour up to the snapshot: the only information the model uses."),
        ("Prediction window", w["prediction"], "rgba(60,157,93,0.55)",
         "The period being predicted. A customer who buys at least once here has returned; one who does not has churned."),
    ]:
        s, e = pd.Timestamp(start), pd.Timestamp(end)
        fig.add_trace(go.Bar(
            y=["What the model sees"], x=[(e - s).total_seconds() * 1000], base=[s], orientation="h",
            marker_color=color, width=0.5, name=name, text=name, textposition="inside", insidetextanchor="middle",
            hovertemplate=f"<b>{name}</b><br>{s:%d %b %Y} to {(e - pd.Timedelta(days=1)):%d %b %Y}<br>"
                          f"{_wrap(text)}<extra></extra>"))

    # Each customer's purchases, and what they mean for this model
    statuses = {}
    for cust, dates in TIMELINE_CUSTOMERS.items():
        d = pd.to_datetime(dates)
        before = d[d < snap]
        after = d[(d >= snap) & (d < pred_end)]
        if len(before) == 0:
            status, color = "New: not scored", "#9AA0AC"
            why = "No purchases before the snapshot, so there is no history to predict from."
        elif len(after) > 0:
            status, color = "Returned", "#3C9D5D"
            why = "Bought at least once in the prediction window."
        else:
            status, color = "Churned", "#D9534F"
            why = "Had a history before the snapshot but bought nothing in the prediction window."
        statuses[cust] = (status, color)
        where = ["in the history" if x < snap else "in the prediction window" for x in d]
        fig.add_trace(go.Scatter(
            x=d, y=[cust] * len(d), mode="markers+lines", line=dict(color="rgba(154,160,172,0.4)", width=1),
            marker=dict(size=14, color=color, line=dict(width=1, color="#9AA0AC")), name=cust,
            customdata=where,
            hovertemplate=f"<b>{cust}: {status}</b><br>Purchase on %{{x|%d %b %Y}}, %{{customdata}}.<br>"
                          f"{_wrap(why)}<extra></extra>"))

    fig.add_vrect(x0=w["prediction"][0], x1=w["prediction"][1], fillcolor="rgba(60,157,93,0.08)", line_width=0)
    fig.add_vline(x=snap, line_dash="dash", line_color="#9AA0AC", line_width=2)
    fig.add_annotation(x=snap, y=1.08, yref="paper", text=f"<b>Snapshot</b> {snap:%d %b %Y}", showarrow=False)
    for cust, (status, color) in statuses.items():
        fig.add_annotation(x=1.01, xref="paper", y=cust, xanchor="left", showarrow=False,
                           text=f"<b>{status}</b>", font=dict(color=color, size=13))

    fig.update_layout(
        height=330, showlegend=False, barmode="overlay", dragmode=False, hovermode="closest",
        margin=dict(l=0, r=130, t=40, b=10),
        xaxis=dict(type="date", range=["2009-11-15", "2011-12-25"], fixedrange=True, tickformat="%b %Y"),
        yaxis=dict(categoryorder="array", categoryarray=rows[::-1], fixedrange=True, title=None),
    )
    return _hover_layout(fig)


def expected_value_demo(key):
    """Two sliders driving the expected-value split bar: the expected value rule, made interactive."""
    c1, c2 = st.columns(2)
    p = c1.slider("Churn risk", 0, 100, 30, 5, format="%d%%", key=f"{key}_p") / 100
    s = c2.slider("Spend if they buy again (£)", 0, 5000, 1000, 50, key=f"{key}_s")
    pred = {"Churn_Prob": p, "Spend_If_Retained": s, "Expected_CLV": (1 - p) * s, "Value_At_Risk": p * s}
    if s >= 1:
        st.plotly_chart(value_split_chart(pred, height=130), width="stretch", config={"displayModeBar": False},
                        key=f"{key}_bar")
    st.markdown(
        f"A customer with a **{p:.0%}** churn risk who would spend **£{s:,.0f}** if they buy again has an "
        f"**expected value of £{(1 - p) * s:,.0f}** (that is, (1 - {p:.2f}) × £{s:,.0f}) and "
        f"**£{p * s:,.0f} at risk** ({p:.2f} × £{s:,.0f}). The two always add up to £{s:,.0f}."
    )


def lift_example(rules, key):
    """A worked example of confidence and lift, per 1,000 orders, for one association rule."""
    top = rules.sort_values("lift", ascending=False).drop_duplicates("antecedents").head(8)
    labels = {i: f"{r.antecedents.strip().title()}  →  {r.consequents.strip().title()}" for i, r in top.iterrows()}
    choice = st.selectbox("Pick a product pair", list(labels), format_func=labels.get, key=f"{key}_rule")
    r = rules.loc[choice]
    a, b = r["antecedents"].strip().title(), r["consequents"].strip().title()
    supp_a = r["support"] / r["confidence"]          # share of orders containing A
    supp_b = r["confidence"] / r["lift"]             # share of orders containing B
    per_k = lambda share: share * 1000

    s1, s2, s3 = st.columns(3)
    with s1.container(border=True, height="stretch"):
        st.markdown("**1. How often is A bought?**")
        st.markdown(f"Out of every 1,000 orders, about **{per_k(supp_a):.0f}** contain *{a}*.")
    with s2.container(border=True, height="stretch"):
        st.markdown("**2. Confidence**")
        st.markdown(f"Of those {per_k(supp_a):.0f}, about **{per_k(r['support']):.0f}** also contain *{b}*: "
                    f"a confidence of **{r['confidence']:.0%}**.")
    with s3.container(border=True, height="stretch"):
        st.markdown("**3. Lift**")
        st.markdown(f"Across all orders, only **{supp_b:.1%}** contain *{b}*. So buying *{a}* makes *{b}* "
                    f"**{r['lift']:.0f} times** as likely ({r['confidence']:.0%} ÷ {supp_b:.1%}).")

    fig = go.Figure(go.Bar(
        x=[supp_b, r["confidence"]], y=["All orders", f"Orders containing {a}"], orientation="h",
        marker_color=["#9AA0AC", "#3A6EA5"], text=[f"{supp_b:.1%}", f"{r['confidence']:.0%}"],
        textposition="outside",
        hovertemplate=[f"Share of all orders that contain {b}: {supp_b:.1%}<extra></extra>",
                       f"Share of orders with {a} that also contain {b}: {r['confidence']:.0%}<extra></extra>"]))
    fig.update_layout(height=170, margin=dict(l=0, r=40, t=30, b=0), dragmode=False,
                      title=dict(text=f"How often {b} is in the basket", font=dict(size=13)),
                      xaxis=dict(tickformat=".0%", range=[0, 1.1], fixedrange=True),
                      yaxis=dict(fixedrange=True, autorange="reversed"))
    st.plotly_chart(_hover_layout(fig), width="stretch", config={"displayModeBar": False}, key=f"{key}_bar")
