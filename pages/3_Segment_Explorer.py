import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import load_data

st.set_page_config(page_title="Segment Explorer", page_icon="🧩", layout="wide")
st.title("Segment Explorer")
st.write("Browse customer segments identified through clustering, their characteristics, and revenue contribution.")

data = load_data()
clusters = data["clusters"]

# Fixed colour per segment so every chart on the page uses the same colours
SEGMENT_COLORS = {
    'Typical Steady': '#4C78A8',
    'High-Value Regulars': '#54A24B',
    'At-Risk/Lapsed': '#E45756',
    'Elite Wholesalers': '#B279A2'
}

# Clean log-axis settings: one tick per power of 10, no "2, 5" minor labels
LOG_AXIS = dict(dtick=1)
LOG_MONEY_AXIS = dict(dtick=1, tickprefix='£', tickformat=',')

# Recency spans under three decades (1 to 555), so it gets intermediate ticks
# on a log scale; otherwise At-Risk (170 to 555) sits above the last label
LOG_RECENCY_AXIS = dict(tickmode='array', tickvals=[1, 2, 5, 10, 20, 50, 100, 200, 500])


# Overview table
segment_summary = clusters.groupby('Segment_Name').agg(
    Customers=('Cluster', 'count'),
    Total_Revenue=('Monetary', 'sum'),
    Avg_Recency=('Recency', 'mean'),
    Avg_Frequency=('Frequency', 'mean'),
    Avg_Monetary=('Monetary', 'mean')
)

segment_summary['% of Customers'] = segment_summary['Customers'] / segment_summary['Customers'].sum() * 100
segment_summary['% of Revenue'] = segment_summary['Total_Revenue'] / segment_summary['Total_Revenue'].sum() * 100

segment_summary = segment_summary[
    ['Customers', '% of Customers', '% of Revenue', 'Total_Revenue',
     'Avg_Recency', 'Avg_Frequency', 'Avg_Monetary']
].sort_values('Total_Revenue', ascending=False)

segment_summary = segment_summary.rename(columns={
    'Total_Revenue': 'Total Revenue',
    'Avg_Recency': 'Avg Recency (days)',
    'Avg_Frequency': 'Avg Frequency',
    'Avg_Monetary': 'Avg Monetary'
})
segment_summary.index.name = 'Segment'

# Segment order used by every chart (largest revenue first)
SEGMENT_ORDER = segment_summary.index.tolist()

st.subheader("Segment Overview")
st.caption(
    "Revenue figures are historical spend during the 18-month calibration period "
    "(2009-12-01 to 2011-06-08), not predicted future CLV."
)
st.dataframe(
    segment_summary.style.format({
        'Customers': '{:,}',
        '% of Customers': '{:.1f}%',
        '% of Revenue': '{:.1f}%',
        'Total Revenue': '£{:,.0f}',
        'Avg Recency (days)': '{:.1f}',
        'Avg Frequency': '{:.1f}',
        'Avg Monetary': '£{:,.0f}'
    }),
    use_container_width=True
)


# Chart 1: customer share vs revenue share (bars or donuts)
st.subheader("Customer Share vs Revenue Share")
st.caption("Where each segment's share of revenue differs from its share of customers, value is concentrated or diluted.")

share_view = st.radio("Chart type", ["Bars", "Donuts"], horizontal=True, key="share_view")

if share_view == "Bars":
    share_df = (
        segment_summary[['% of Customers', '% of Revenue']]
        .reset_index()
        .melt(id_vars='Segment', var_name='Measure', value_name='Percent')
    )

    fig_share = px.bar(
        share_df,
        x='Segment',
        y='Percent',
        color='Measure',
        barmode='group',
        text_auto='.1f',
        category_orders={'Segment': SEGMENT_ORDER},
        color_discrete_map={'% of Customers': '#9E9E9E', '% of Revenue': '#4C78A8'},
        labels={'Percent': '% of total'}
    )
    fig_share.update_layout(height=420, legend_title_text='')

else:
    slice_colors = [SEGMENT_COLORS[s] for s in SEGMENT_ORDER]
    total_customers = segment_summary['Customers'].sum()
    total_revenue = segment_summary['Total Revenue'].sum()

    fig_share = make_subplots(
        rows=1, cols=2,
        specs=[[{'type': 'domain'}, {'type': 'domain'}]]
    )

    fig_share.add_trace(
        go.Pie(
            labels=SEGMENT_ORDER,
            values=segment_summary.loc[SEGMENT_ORDER, 'Customers'],
            hole=0.55,
            sort=False,
            direction='clockwise',
            marker=dict(colors=slice_colors),
            texttemplate='%{percent:.1%}',
            textposition='inside',
            title=dict(text=f"Customers<br>{total_customers:,}", position='middle center'),
            hovertemplate='%{label}<br>%{value:,} customers<br>%{percent:.1%}<extra></extra>',
            name='Customers'
        ),
        row=1, col=1
    )

    fig_share.add_trace(
        go.Pie(
            labels=SEGMENT_ORDER,
            values=segment_summary.loc[SEGMENT_ORDER, 'Total Revenue'],
            hole=0.55,
            sort=False,
            direction='clockwise',
            marker=dict(colors=slice_colors),
            texttemplate='%{percent:.1%}',
            textposition='inside',
            title=dict(text=f"Revenue<br>£{total_revenue/1e6:,.2f}M", position='middle center'),
            hovertemplate='%{label}<br>£%{value:,.0f}<br>%{percent:.1%}<extra></extra>',
            name='Revenue'
        ),
        row=1, col=2
    )

    fig_share.update_layout(
        height=460,
        legend_title_text='Segment',
        uniformtext_minsize=11,
        uniformtext_mode='hide'
    )

st.plotly_chart(fig_share, use_container_width=True)

st.divider()


# Chart 2: segment map (2D / 3D)
st.subheader("Segment Map")
st.caption(
    "Each point is one customer. Hover for details, drag to zoom (2D) or rotate (3D), double-click to reset. "
    "Click a segment in the legend to hide it, double-click to show only that segment. "
    "Monetary (and Frequency in 3D) use a log scale because values span over 1,000x."
)

plot_df = clusters.reset_index()
id_col = 'Customer ID' if 'Customer ID' in plot_df.columns else plot_df.columns[0]

view = st.radio(
    "View",
    ["2D: Recency vs Monetary", "3D: Recency, Frequency, Monetary"],
    horizontal=True
)

hover = {
    id_col: ':.0f',
    'Recency': True,
    'Frequency': True,
    'Monetary': ':,.2f',
    'Segment_Name': False
}

if view.startswith("2D"):
    fig_map = px.scatter(
        plot_df,
        x='Recency',
        y='Monetary',
        color='Segment_Name',
        color_discrete_map=SEGMENT_COLORS,
        category_orders={'Segment_Name': SEGMENT_ORDER},
        log_y=True,
        opacity=0.6,
        hover_data=hover,
        labels={'Recency': 'Recency (days)', 'Monetary': 'Monetary (log scale)'}
    )
    fig_map.update_traces(marker=dict(size=6))
    fig_map.update_yaxes(**LOG_MONEY_AXIS)
else:
    fig_map = px.scatter_3d(
        plot_df,
        x='Recency',
        y='Frequency',
        z='Monetary',
        color='Segment_Name',
        color_discrete_map=SEGMENT_COLORS,
        category_orders={'Segment_Name': SEGMENT_ORDER},
        log_y=True,
        log_z=True,
        opacity=0.7,
        hover_data=hover,
        labels={
            'Recency': 'Recency (days)',
            'Frequency': 'Frequency (log)',
            'Monetary': 'Monetary (log)'
        }
    )
    fig_map.update_traces(marker=dict(size=3))
    fig_map.update_layout(
        scene=dict(
            xaxis=dict(tickfont=dict(size=10)),
            yaxis=dict(**LOG_AXIS, tickfont=dict(size=10)),
            zaxis=dict(**LOG_MONEY_AXIS, tickfont=dict(size=10))
        ),
        scene_camera=dict(eye=dict(x=1.8, y=1.5, z=0.9)),
        margin=dict(l=0, r=0, t=20, b=0)
    )

# itemsizing='constant' keeps legend symbols readable regardless of marker size
fig_map.update_layout(
    height=600,
    legend=dict(title_text='Segment', itemsizing='constant')
)
st.plotly_chart(fig_map, use_container_width=True)

# Closure explanation only applies to the 2D view, where the gaps are visible
if view.startswith("2D"):
    st.caption(
        "Empty vertical bands are store closures, when no customer could have made a purchase: "
        "Christmas/New Year (24 Dec to 3 Jan, both years) and the Easter weekend "
        "(2 to 5 Apr 2010, 22 to 25 Apr 2011)."
    )

st.divider()

# Chart 3: distribution comparison
st.subheader("Compare Distributions Across Segments")
st.caption(
    "Box = middle 50% of customers (25th to 75th percentile), line = median, "
    "whiskers = typical range, dots = outliers beyond 1.5x the box height."
)

col_m, col_l = st.columns([3, 1])
metric = col_m.selectbox("Metric", ['Recency', 'Frequency', 'Monetary'])
use_log = col_l.checkbox("Log scale", value=(metric != 'Recency'))

fig_box = px.box(
    plot_df,
    x='Segment_Name',
    y=metric,
    color='Segment_Name',
    color_discrete_map=SEGMENT_COLORS,
    category_orders={'Segment_Name': SEGMENT_ORDER},
    points='outliers',
    log_y=use_log,
    hover_data={id_col: ':.0f'},
    labels={'Segment_Name': 'Segment'}
)
fig_box.update_layout(height=480, showlegend=False)

if use_log:
    if metric == 'Monetary':
        fig_box.update_yaxes(**LOG_MONEY_AXIS)
    elif metric == 'Recency':
        fig_box.update_yaxes(**LOG_RECENCY_AXIS)
    else:
        fig_box.update_yaxes(**LOG_AXIS)
elif metric == 'Monetary':
    fig_box.update_yaxes(tickprefix='£', tickformat=',')

st.plotly_chart(fig_box, use_container_width=True)

st.divider()

# Drill-down
st.subheader("Explore a Segment")
selected_segment = st.selectbox("Select a segment to explore", SEGMENT_ORDER)

segment_customers = clusters[clusters['Segment_Name'] == selected_segment]

col1, col2, col3 = st.columns(3)
col1.metric("Customers in Segment", f"{len(segment_customers):,}")
col2.metric("Avg Monetary", f"£{segment_customers['Monetary'].mean():,.2f}")
col3.metric("Avg Frequency", f"{segment_customers['Frequency'].mean():.1f} orders")

st.write(f"**Sample customers in {selected_segment}:**")
sample = segment_customers.sample(min(10, len(segment_customers)), random_state=42)
sample = sample[['Recency', 'Frequency', 'Monetary']]
st.dataframe(
    sample.style.format({
        'Recency': '{:.0f}',
        'Frequency': '{:.0f}',
        'Monetary': '£{:,.2f}'
    }),
    use_container_width=False,
    column_config={'Monetary': st.column_config.Column(width='medium')}
)