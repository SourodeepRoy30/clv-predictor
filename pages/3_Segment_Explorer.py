import streamlit as st
import sys
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import load_data, by_customer_id, SEGMENT_COLORS
from definitions import GLOSSARY, tip
from ui import page_header, segment_badge

page_header(
    "Segment Explorer",
    "What kinds of customers are there?",
    how_to="""
**What this page shows:** customers grouped into four segments by how recently, how often and how much they buy, found by clustering.

**How to use it:**
- The cards at the top summarise each segment.
- The tabs below let you compare segments: their share of customers and revenue, where their customers sit on a map, how their behaviour is spread, and individual customers.
- In **Browse customers**, click a row to open that customer in Customer Lookup.

**Good to know:** revenue here is past spend over the 18 months to June 2011, not a prediction. Most customers lie on a continuous spectrum, so the line between the two large segments is an approximation.
""",
)

data = load_data()
clusters = by_customer_id(data["clusters"])

summary = clusters.groupby('Segment_Name').agg(
    Customers=('Cluster', 'count'), Revenue=('Monetary', 'sum'),
    Recency=('Recency', 'mean'), Frequency=('Frequency', 'mean'), Monetary=('Monetary', 'mean'))
summary['Customer_Share'] = summary['Customers'] / summary['Customers'].sum()
summary['Revenue_Share'] = summary['Revenue'] / summary['Revenue'].sum()
summary = summary.sort_values('Revenue', ascending=False)
SEGMENT_ORDER = summary.index.tolist()


# Segment cards and summary
for col, seg in zip(st.columns(len(SEGMENT_ORDER)), SEGMENT_ORDER):
    row = summary.loc[seg]
    with col.container(border=True, height="stretch"):
        st.markdown(segment_badge(seg))
        st.metric("Share of revenue", f"{row['Revenue_Share']:.1%}",
                  f"{row['Customer_Share']:.1%} of customers", delta_color="off", delta_arrow="off")
        st.caption(GLOSSARY.get(seg, {}).get("short", ""))

top = ["Elite Wholesalers", "High-Value Regulars"]
present_top = [s for s in top if s in summary.index]
if present_top and "Typical Steady" in summary.index and "At-Risk/Lapsed" in summary.index:
    st.info(
        f"The two highest-value segments are **{summary.loc[present_top, 'Customer_Share'].sum():.1%} of customers** "
        f"but bring in **{summary.loc[present_top, 'Revenue_Share'].sum():.1%} of revenue**. Typical Steady customers "
        f"bring in the most revenue overall ({summary.loc['Typical Steady', 'Revenue_Share']:.1%}) simply because there "
        f"are so many of them, while At-Risk/Lapsed customers are {summary.loc['At-Risk/Lapsed', 'Customer_Share']:.1%} "
        f"of customers but only {summary.loc['At-Risk/Lapsed', 'Revenue_Share']:.1%} of revenue.",
        icon=":material/lightbulb:",
    )

tab_share, tab_map, tab_compare, tab_browse = st.tabs(
    ["Customers vs revenue", "Segment map", "Compare behaviour", "Browse customers"])

LOG_AXIS = dict(dtick=1)
LOG_MONEY_AXIS = dict(dtick=1, tickprefix='£', tickformat=',')
LOG_RECENCY_AXIS = dict(tickmode='array', tickvals=[1, 2, 5, 10, 20, 50, 100, 200, 500])
plot_df = clusters.reset_index()


# Customers vs revenue
with tab_share:
    view = st.segmented_control("Chart", ["Bars", "Donuts"], default="Bars", key="share_view")
    if view == "Donuts":
        fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'domain'}, {'type': 'domain'}]])
        for i, (measure, title) in enumerate([("Customers", f"Customers<br>{summary['Customers'].sum():,}"),
                                              ("Revenue", f"Revenue<br>£{summary['Revenue'].sum() / 1e6:,.2f}M")]):
            fig.add_trace(go.Pie(
                labels=SEGMENT_ORDER, values=summary.loc[SEGMENT_ORDER, measure], hole=0.55, sort=False,
                direction='clockwise', marker=dict(colors=[SEGMENT_COLORS[s] for s in SEGMENT_ORDER]),
                texttemplate='%{percent:.1%}', textposition='inside',
                title=dict(text=title, position='middle center'), name=measure,
                hovertemplate='%{label}<br>%{percent:.1%}<extra></extra>'), row=1, col=i + 1)
        fig.update_layout(height=440, legend_title_text='', uniformtext_minsize=11, uniformtext_mode='hide')
    else:
        share_df = (summary[['Customer_Share', 'Revenue_Share']]
                    .rename(columns={'Customer_Share': 'Share of customers', 'Revenue_Share': 'Share of revenue'})
                    .reset_index().melt(id_vars='Segment_Name', var_name='Measure', value_name='Share'))
        fig = px.bar(share_df, x='Segment_Name', y='Share', color='Measure', barmode='group', text_auto='.1%',
                     category_orders={'Segment_Name': SEGMENT_ORDER},
                     color_discrete_map={'Share of customers': '#9AA0AC', 'Share of revenue': '#3A6EA5'},
                     labels={'Segment_Name': '', 'Share': ''})
        fig.update_yaxes(tickformat='.0%')
        fig.update_layout(height=420, legend=dict(title_text='', orientation='h', y=1.1))
    st.plotly_chart(fig, width="stretch")

    table = summary[['Customers', 'Customer_Share', 'Revenue_Share', 'Revenue', 'Recency', 'Frequency', 'Monetary']]
    st.dataframe(
        table.style.format({'Customers': '{:,}', 'Customer_Share': '{:.1%}', 'Revenue_Share': '{:.1%}',
                            'Revenue': '£{:,.0f}', 'Recency': '{:.0f}', 'Frequency': '{:.1f}',
                            'Monetary': '£{:,.0f}'}),
        width="stretch",
        column_config={
            "Segment_Name": "Segment",
            "Customer_Share": "Share of customers", "Revenue_Share": "Share of revenue",
            "Revenue": st.column_config.Column("Total spend", help="Spend during the 18 months to 2011-06-08."),
            "Recency": st.column_config.Column("Avg days since last order", help=tip("Recency")),
            "Frequency": st.column_config.Column("Avg orders", help=tip("Frequency")),
            "Monetary": st.column_config.Column("Avg spend", help=tip("Monetary")),
        },
    )

# Segment map
with tab_map:
    dims = st.segmented_control("View", ["2D", "3D"], default="2D", key="map_view",
                                help="2D: days since last order against total spend. 3D adds number of orders.")
    hover = {'Customer ID': True, 'Recency': True, 'Frequency': True, 'Monetary': ':,.0f', 'Segment_Name': False}
    common = dict(color='Segment_Name', color_discrete_map=SEGMENT_COLORS,
                  category_orders={'Segment_Name': SEGMENT_ORDER}, hover_data=hover)
    if dims == "3D":
        fig = px.scatter_3d(plot_df, x='Recency', y='Frequency', z='Monetary', log_y=True, log_z=True, opacity=0.7,
                            labels={'Recency': 'Days since last order', 'Frequency': 'Orders (log)',
                                    'Monetary': 'Total spend (log)'}, **common)
        fig.update_traces(marker=dict(size=3))
        fig.update_layout(scene=dict(yaxis=dict(**LOG_AXIS), zaxis=dict(**LOG_MONEY_AXIS)),
                          scene_camera=dict(eye=dict(x=1.8, y=1.5, z=0.9)), margin=dict(l=0, r=0, t=20, b=0))
    else:
        fig = px.scatter(plot_df, x='Recency', y='Monetary', log_y=True, opacity=0.6,
                         labels={'Recency': 'Days since last order', 'Monetary': 'Total spend (log scale)'}, **common)
        fig.update_traces(marker=dict(size=6))
        fig.update_yaxes(**LOG_MONEY_AXIS)
    fig.update_layout(height=600, legend=dict(title_text='', orientation='h', y=-0.12, itemsizing='constant'))
    st.plotly_chart(fig, width="stretch")
    st.caption("Each point is one customer: hover for details, drag to zoom (or rotate in 3D), double-click to reset, "
               "click a segment in the legend to hide it. Spend uses a log scale because it varies over 1,000-fold.")
    if dims != "3D":
        st.caption("The empty vertical bands are store closures: Christmas to New Year and the Easter weekend.")


# Compare behaviour
with tab_compare:
    METRICS = {"Days since last order": "Recency", "Number of orders": "Frequency", "Total spend": "Monetary"}
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    metric_label = c1.segmented_control("Compare", list(METRICS), default="Total spend", key="compare_metric")
    metric = METRICS[metric_label or "Total spend"]
    use_log = c2.toggle("Log scale", value=(metric != 'Recency'), key=f"log_{metric}",
                        help="Spreads out values that range over several orders of magnitude.")
    fig = px.box(plot_df, x='Segment_Name', y=metric, color='Segment_Name', color_discrete_map=SEGMENT_COLORS,
                 category_orders={'Segment_Name': SEGMENT_ORDER}, points='outliers', log_y=use_log,
                 hover_data={'Customer ID': True}, labels={'Segment_Name': '', metric: metric_label})
    fig.update_layout(height=480, showlegend=False)
    if use_log:
        fig.update_yaxes(**(LOG_MONEY_AXIS if metric == 'Monetary' else LOG_RECENCY_AXIS if metric == 'Recency'
                            else LOG_AXIS))
    elif metric == 'Monetary':
        fig.update_yaxes(tickprefix='£', tickformat=',')
    st.plotly_chart(fig, width="stretch")
    st.caption("Each box covers the middle half of a segment's customers; the line inside is the median, and dots "
               "are unusual customers. Averages hide how spread out a segment is; boxes show it.")


# Browse customers
with tab_browse:
    chosen = st.segmented_control("Segment", SEGMENT_ORDER, default=SEGMENT_ORDER[0], key="browse_segment")
    chosen = chosen or SEGMENT_ORDER[0]
    members = clusters[clusters['Segment_Name'] == chosen]
    b1, b2, b3 = st.columns(3)
    b1.metric("Customers", f"{len(members):,}", border=True)
    b2.metric("Average spend", f"£{members['Monetary'].mean():,.0f}", help=tip("Monetary"), border=True)
    b3.metric("Average orders", f"{members['Frequency'].mean():.1f}", help=tip("Frequency"), border=True)

    sample = members.sample(min(10, len(members)), random_state=42)[['Recency', 'Frequency', 'Monetary']]
    st.caption(f"A sample of {len(sample)} customers. Click a row to open that customer in Customer Lookup.")
    event = st.dataframe(
        sample.style.format({'Monetary': '£{:,.0f}'}),
        width="content", on_select="rerun", selection_mode="single-row", key="browse_table",
        column_config={"Recency": "Days since last order", "Frequency": "Orders", "Monetary": "Total spend"},
    )
    if event.selection.rows:
        st.session_state["lookup_customer"] = int(sample.index[event.selection.rows[0]])
        st.switch_page("pages/1_Customer_Lookup.py")
