import streamlit as st
import sys
import os
import plotly.express as px

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import (load_models, load_data, load_configs, predict_clv, by_customer_id,
                       FEATURE_COLS, SEGMENT_COLORS)
from definitions import tip
from ui import page_header

page_header(
    "At-Risk Customers",
    "Who should we contact first?",
    how_to="""
**What this page shows:** a retention list. Every customer is scored on how likely they are to stop buying in the next 6 months, and how much revenue would be lost if they do.

**How to use it:**
1. Choose **who to include**: a minimum churn risk and the segments of interest.
2. Set your **campaign assumptions**: what one contact costs, and what share of contacted customers you expect to win back. The defaults are placeholders.
3. Read the list from the top: customers are ranked by **value at risk**, so the most valuable customers who might leave come first.

**How to read the list:** *Net benefit* is the expected revenue saved by contacting a customer, minus the cost of contacting them. Contacting is worthwhile only when it is positive. Download the list as a CSV to use in an email or CRM tool.

Scores use behaviour up to 2011-06-08, predicting the following 6 months.
""",
)

models = load_models()
configs = load_configs()
data = load_data()

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
with st.container(border=True):
    who_col, campaign_col = st.columns(2, gap="large")
    with who_col:
        st.markdown("**Who to include**")
        min_prob = st.slider("Minimum churn risk", 0.0, 1.0, 0.5, 0.05, format="%.2f", help=tip("Churn risk"))
    with campaign_col:
        st.markdown("**Campaign assumptions**")
        contact_cost = st.number_input("Cost per contact (£)", min_value=0.0, max_value=1000.0, value=5.0,
                                       step=1.0, help=tip("Cost per contact"))
        success_rate = st.slider("Retention success rate (%)", 0, 100, 20, 5,
                                 help=tip("Retention success rate")) / 100
    # Full width below both halves, so all four segment chips fit
    segments = st.pills("Segments to include", SEGMENT_ORDER, selection_mode="multi", default=SEGMENT_ORDER,
                        help=tip("Segment"))

scored['Net_Benefit'] = success_rate * scored['Value_At_Risk'] - contact_cost
flagged = (scored[(scored['Churn_Prob'] >= min_prob) & (scored['Segment'].isin(segments))]
           .sort_values('Value_At_Risk', ascending=False))
worth_contacting = flagged[flagged['Net_Benefit'] > 0]

# Summary
if flagged.empty:
    st.info("No customers match these filters. Lower the minimum churn risk or add segments.", icon=":material/info:")
else:
    top_id, top = flagged.index[0], flagged.iloc[0]
    st.info(
        f"**{len(flagged):,} of {len(scored):,} customers** have a churn risk of {min_prob:.0%} or more, putting "
        f"**£{flagged['Value_At_Risk'].sum():,.0f}** of 6-month revenue at risk. With these campaign assumptions, "
        f"contacting the **{len(worth_contacting):,}** for whom it pays off is expected to return "
        f"**£{worth_contacting['Net_Benefit'].sum():,.0f}** after costs. "
        f"Top of the list: customer {top_id} ({top['Segment']}), with £{top['Value_At_Risk']:,.0f} at risk.",
        icon=":material/campaign:",
    )

m1, m2, m3, m4 = st.columns(4)
m1.metric("Customers in scope", f"{len(flagged):,}", border=True)
m2.metric("6-month revenue at risk", f"£{flagged['Value_At_Risk'].sum():,.0f}", help=tip("Value at risk"), border=True)
m3.metric("Worth contacting", f"{len(worth_contacting):,}", help="Customers with a positive net benefit.", border=True)
m4.metric("Expected net benefit", f"£{worth_contacting['Net_Benefit'].sum():,.0f}", help=tip("Net benefit"),
          border=True)

tab_list, tab_chart = st.tabs(["Retention list", "Risk vs value"])


# Retention list
with tab_list:
    table = flagged[['Segment', 'Churn_Prob', 'Value_At_Risk', 'Net_Benefit', 'Expected_CLV',
                     'Spend_If_Retained', 'Recency', 'Frequency', 'Monetary']]
    money_cols = ['Value_At_Risk', 'Net_Benefit', 'Expected_CLV', 'Spend_If_Retained', 'Monetary']
    st.dataframe(
        table.style.format({c: '£{:,.0f}' for c in money_cols}),
        width="stretch",
        height=460,
        column_config={
            "Segment": st.column_config.TextColumn("Segment"),
            "Churn_Prob": st.column_config.ProgressColumn("Churn risk", min_value=0, max_value=1, format="percent",
                                                          help=tip("Churn risk")),
            "Value_At_Risk": st.column_config.Column("Value at risk", help=tip("Value at risk")),
            "Net_Benefit": st.column_config.Column("Net benefit", help=tip("Net benefit")),
            "Expected_CLV": st.column_config.Column("Expected value", help=tip("Expected CLV")),
            "Spend_If_Retained": st.column_config.Column("Spend if retained", help=tip("Spend if retained")),
            "Recency": st.column_config.NumberColumn("Days since last order", help=tip("Recency")),
            "Frequency": st.column_config.NumberColumn("Orders", help=tip("Frequency")),
            "Monetary": st.column_config.Column("Historical spend", help=tip("Monetary")),
        },
    )
    download = table.rename(columns={
        'Churn_Prob': 'Churn Risk', 'Value_At_Risk': 'Value at Risk', 'Net_Benefit': 'Net Benefit',
        'Expected_CLV': 'Expected CLV', 'Spend_If_Retained': 'Spend if Retained', 'Recency': 'Days Since Last Order',
        'Frequency': 'Orders', 'Monetary': 'Historical Spend'})
    st.download_button("Download this list (CSV)", download.to_csv().encode('utf-8'), "at_risk_customers.csv",
                       "text/csv", icon=":material/download:")


# Risk vs value chart
with tab_chart:
    st.caption("Each point is a customer. The most important retention targets sit top right: likely to leave "
               "and valuable if kept. The dashed line is your minimum churn risk.")
    plot_df = scored[scored['Segment'].isin(segments) & (scored['Spend_If_Retained'] > 0)].reset_index()
    fig = px.scatter(
        plot_df, x='Churn_Prob', y='Spend_If_Retained', color='Segment',
        color_discrete_map=SEGMENT_COLORS, category_orders={'Segment': SEGMENT_ORDER},
        log_y=True, opacity=0.6,
        hover_data={'Customer ID': True, 'Churn_Prob': ':.1%', 'Spend_If_Retained': ':,.0f',
                    'Value_At_Risk': ':,.0f', 'Segment': False},
        labels={'Churn_Prob': 'Churn risk (6 months)', 'Spend_If_Retained': 'Spend if retained (log scale)',
                'Value_At_Risk': 'Value at risk'},
    )
    fig.update_traces(marker=dict(size=6))
    fig.update_xaxes(tickformat='.0%', range=[0, 1])
    fig.update_yaxes(dtick=1, tickprefix='£', tickformat=',')
    fig.add_vline(x=min_prob, line_dash='dash', line_color='#9AA0AC')
    fig.update_layout(height=520, legend=dict(title_text='', orientation='h', y=-0.18, itemsizing='constant'))
    st.plotly_chart(fig, width="stretch")
    excluded = (scored['Segment'].isin(segments) & (scored['Spend_If_Retained'] <= 0)).sum()
    if excluded:
        st.caption(f"Not shown: {excluded:,} customers whose predicted spend if retained is £0 "
                   "(a log scale cannot display zero).")
