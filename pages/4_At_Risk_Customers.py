import streamlit as st
import sys
import os
import numpy as np
import pandas as pd
import plotly.express as px

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import (load_models, load_data, load_configs, predict_clv, by_customer_id,
                       describe_config, FEATURE_COLS, SEGMENT_COLORS)

st.set_page_config(page_title="At-Risk Customers", page_icon="⚠️", layout="wide")
models = load_models()
configs = load_configs()
data = load_data()

st.title("At-Risk Customers")
st.write(
    "A ranked retention list: which customers are likely to churn in the next 6 months, "
    "how much revenue is at stake, and whether contacting them is worth the cost."
)
st.caption(
    "Scores use each customer's behaviour as of the 2011-06-09 snapshot (end of the calibration period), "
    "the same basis as Customer Lookup. All values are 6-month revenue. "
    f"Model: {describe_config(configs['clv_6mo'])}; value at risk = churn probability x spend if retained."
)


SEGMENT_ORDER = ['Typical Steady', 'High-Value Regulars', 'At-Risk/Lapsed', 'Elite Wholesalers']


@st.cache_data
def score_customers(_models, _configs, modeling_table, clusters):
    """Score every customer once: churn probability, spend if retained, expected CLV, value at risk."""
    modeling_table = by_customer_id(modeling_table)
    clusters = by_customer_id(clusters)

    scored = modeling_table[['Recency', 'Frequency', 'Monetary']].copy()
    scored = scored.join(predict_clv(_models, _configs, "6mo", modeling_table[FEATURE_COLS]))
    scored['Segment'] = clusters['Segment_Name'].reindex(scored.index)
    return scored


scored = score_customers(models, configs, data['modeling_table'], data['clusters'])

if scored['Segment'].isna().any():
    st.warning(f"{scored['Segment'].isna().sum()} customers could not be matched to a segment.")


# Controls
st.subheader("Filters")
col_a, col_b, col_c = st.columns([2, 1, 3])
min_prob = col_a.slider("Minimum churn probability", 0.0, 1.0, 0.5, 0.05)
rank_by = col_b.radio("Rank by", ["Value at risk", "Churn probability"])
segments = col_c.multiselect("Segments", SEGMENT_ORDER, default=SEGMENT_ORDER)

with st.expander("Campaign economics", expanded=True):
    st.caption(
        "Net benefit = success rate x churn probability x spend if retained - cost per contact. "
        "Contact a customer only if net benefit is positive. Defaults are placeholders, set them to your campaign's real figures."
    )
    col_e1, col_e2 = st.columns(2)
    contact_cost = col_e1.number_input("Cost per contact (£)", min_value=0.0, max_value=1000.0, value=5.0, step=1.0)
    success_rate = col_e2.slider("Retention success rate (%)", 0, 100, 20, 5) / 100

scored['Net_Benefit'] = success_rate * scored['Value_At_Risk'] - contact_cost

flagged = scored[(scored['Churn_Prob'] >= min_prob) & (scored['Segment'].isin(segments))]
sort_col = 'Value_At_Risk' if rank_by == "Value at risk" else 'Churn_Prob'
flagged = flagged.sort_values(sort_col, ascending=False)

worth_contacting = flagged[flagged['Net_Benefit'] > 0]


# Summary metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Customers flagged", f"{len(flagged):,}")
m2.metric("6-month revenue at risk", f"£{flagged['Value_At_Risk'].sum():,.0f}")
m3.metric("Worth contacting", f"{len(worth_contacting):,}")
m4.metric("Expected net benefit", f"£{worth_contacting['Net_Benefit'].sum():,.0f}")

st.divider()


# Chart: churn probability vs spend if retained
st.subheader("Risk vs Value")
st.caption(
    "Each point is one customer. Top-right customers are both likely to churn and valuable if kept: "
    "the priority retention targets. The dashed line is your minimum churn probability."
)

plot_df = scored[scored['Segment'].isin(segments)].reset_index()
plot_df = plot_df[plot_df['Spend_If_Retained'] > 0]

fig = px.scatter(
    plot_df,
    x='Churn_Prob',
    y='Spend_If_Retained',
    color='Segment',
    color_discrete_map=SEGMENT_COLORS,
    category_orders={'Segment': SEGMENT_ORDER},
    log_y=True,
    opacity=0.6,
    hover_data={
        'Customer ID': True,
        'Churn_Prob': ':.1%',
        'Spend_If_Retained': ':,.2f',
        'Value_At_Risk': ':,.2f',
        'Segment': False
    },
    labels={
        'Churn_Prob': 'Churn probability (6-month)',
        'Spend_If_Retained': 'Spend if retained (log scale)',
        'Value_At_Risk': 'Value at risk'
    }
)
fig.update_traces(marker=dict(size=6))
fig.update_xaxes(tickformat='.0%', range=[0, 1])
fig.update_yaxes(dtick=1, tickprefix='£', tickformat=',')
fig.add_vline(x=min_prob, line_dash='dash', line_color='#AAAAAA')
fig.update_layout(height=520, legend=dict(title_text='Segment', itemsizing='constant'))
st.plotly_chart(fig, use_container_width=True)

excluded = (scored['Segment'].isin(segments) & (scored['Spend_If_Retained'] <= 0)).sum()
if excluded:
    st.caption(f"{excluded:,} customers with a predicted spend of £0 are not shown (a log axis cannot display zero).")

st.divider()


# Ranked table + download
st.subheader("Retention List")
st.caption(f"Ranked by {rank_by.lower()}. Rows with negative net benefit cost more to contact than they are expected to return.")

table = flagged[
    ['Segment', 'Churn_Prob', 'Value_At_Risk', 'Expected_CLV', 'Spend_If_Retained', 'Net_Benefit',
     'Recency', 'Frequency', 'Monetary']
].rename(columns={
    'Churn_Prob': 'Churn Probability',
    'Value_At_Risk': 'Value at Risk',
    'Expected_CLV': 'Expected CLV',
    'Spend_If_Retained': 'Spend if Retained',
    'Net_Benefit': 'Net Benefit',
    'Monetary': 'Historical Spend'
})

st.dataframe(
    table.style.format({
        'Churn Probability': '{:.1%}',
        'Value at Risk': '£{:,.2f}',
        'Expected CLV': '£{:,.2f}',
        'Spend if Retained': '£{:,.2f}',
        'Net Benefit': '£{:,.2f}',
        'Recency': '{:.0f}',
        'Frequency': '{:.0f}',
        'Historical Spend': '£{:,.2f}'
    }),
    use_container_width=True,
    height=450
)

st.download_button(
    label="Download retention list (CSV)",
    data=table.to_csv().encode('utf-8'),
    file_name="at_risk_customers.csv",
    mime="text/csv"
)