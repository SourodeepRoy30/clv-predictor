import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import load_data, SEGMENT_COLORS

st.set_page_config(page_title="Product Insights", page_icon="📦", layout="wide")
st.title("Product Insights")
st.write(
    "Which products drive revenue, when they sell, what customers buy alongside them, "
    "and which customer segments buy them."
)
st.caption(
    "Based on all cleaned transactions from 2009-12-01 to 2011-12-09, with cancelled orders netted out. "
    "Product associations use UK orders only."
)

data = load_data()
products = data["product_summary"]
monthly = data["product_monthly"]
rules = data["association_rules"]
by_segment = data["product_segment"]

# ---------------------------------------------------------------
# 1. Top products
# ---------------------------------------------------------------
st.subheader("Top Products")

RANK_OPTIONS = {
    "Total revenue": "Total_Revenue",
    "Units sold": "Total_Units_Sold",
    "Number of orders": "Order_Count",
    "Revenue per order": "Revenue_Per_Order",
}

col_a, col_b, col_c = st.columns([2, 1, 2])
rank_label = col_a.selectbox("Rank by", list(RANK_OPTIONS))
top_n = col_b.slider("How many", 5, 50, 15, 5)
hide_flagged = col_c.checkbox(
    "Hide single-order-driven products", value=False,
    help="Products with at least £5,000 of revenue where one order supplies half or more of it."
)

ranked = products.copy()
if rank_label == "Revenue per order":
    # A product with one or two orders can top this ranking by chance, so require at least 5 orders
    ranked = ranked[ranked["Order_Count"] >= 5]
    st.caption("Revenue per order is shown for products with at least 5 orders.")
if hide_flagged:
    ranked = ranked[~ranked["Is_Outlier_Driven"]]
ranked = ranked.sort_values(RANK_OPTIONS[rank_label], ascending=False).head(top_n)

fig_top = px.bar(
    ranked.iloc[::-1],
    x=RANK_OPTIONS[rank_label],
    y="Description",
    orientation="h",
    color="Is_Outlier_Driven",
    color_discrete_map={False: "#4C78A8", True: "#E45756"},
    hover_data={"Total_Revenue": ":,.0f", "Order_Count": ":,", "Top_Order_Share": ":.1%", "Is_Outlier_Driven": False},
    labels={RANK_OPTIONS[rank_label]: rank_label, "Description": "",
            "Total_Revenue": "Total revenue (£)", "Order_Count": "Orders", "Top_Order_Share": "Largest order's share"},
)
fig_top.update_layout(height=max(350, 28 * len(ranked)), showlegend=False)
if rank_label in ("Total revenue", "Revenue per order"):
    fig_top.update_xaxes(tickprefix="£", tickformat=",")
st.plotly_chart(fig_top, use_container_width=True)

if ranked["Is_Outlier_Driven"].any():
    st.caption("Red bars: single-order-driven products, where one order supplies half or more of the product's revenue.")

table = ranked[["Description", "Total_Revenue", "Total_Units_Sold", "Order_Count",
                "Revenue_Per_Order", "Top_Order_Share", "Is_Outlier_Driven"]].rename(columns={
    "Total_Revenue": "Total Revenue",
    "Total_Units_Sold": "Units Sold",
    "Order_Count": "Orders",
    "Revenue_Per_Order": "Revenue per Order",
    "Top_Order_Share": "Largest Order's Share",
    "Is_Outlier_Driven": "Single-Order Driven",
})
st.dataframe(
    table.style.format({
        "Total Revenue": "£{:,.0f}",
        "Units Sold": "{:,.0f}",
        "Orders": "{:,.0f}",
        "Revenue per Order": "£{:,.2f}",
        "Largest Order's Share": "{:.1%}",
    }),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ---------------------------------------------------------------
# 2. Seasonality
# ---------------------------------------------------------------
st.subheader("Seasonality")
st.caption(
    "Monthly revenue for the selected products. December 2011 is a partial month (data ends on the 9th), "
    "so its lower value is not a real decline."
)

all_months = sorted(monthly["Month"].unique())
product_options = products.sort_values("Total_Revenue", ascending=False)["Description"].tolist()

col_s1, col_s2 = st.columns([3, 1])
selected_products = col_s1.multiselect(
    "Products (largest by revenue listed first)",
    product_options,
    default=product_options[:5],
    max_selections=8,
)
as_share = col_s2.radio("Show", ["Revenue (£)", "Share of the product's total"], index=0)

if selected_products:
    season = monthly[monthly["Description"].isin(selected_products)]
    season = season.groupby(["Description", "Month"], as_index=False)["Revenue"].sum()

    # Include months with no sales as zero, so lines don't skip over them
    full_grid = pd.MultiIndex.from_product([selected_products, all_months], names=["Description", "Month"])
    season = season.set_index(["Description", "Month"]).reindex(full_grid, fill_value=0).reset_index()

    y_col = "Revenue"
    if as_share != "Revenue (£)":
        season["Share"] = season["Revenue"] / season.groupby("Description")["Revenue"].transform("sum")
        y_col = "Share"

    fig_season = px.line(
        season, x="Month", y=y_col, color="Description", markers=True,
        labels={"Revenue": "Revenue (£)", "Share": "Share of product's total revenue", "Description": "Product"},
    )
    if y_col == "Share":
        fig_season.update_yaxes(tickformat=".0%")
    else:
        fig_season.update_yaxes(tickprefix="£", tickformat=",")
    fig_season.add_vrect(x0=all_months[-2], x1=all_months[-1], fillcolor="gray", opacity=0.15,
                         line_width=0, annotation_text="partial month", annotation_position="top left")
    fig_season.update_layout(height=480, legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig_season, use_container_width=True)
    st.caption(
        "Tip: \"Share of the product's total\" puts products of very different sizes on one scale, "
        "so seasonal shapes can be compared directly."
    )
else:
    st.info("Select at least one product.")

st.divider()

# ---------------------------------------------------------------
# 3. Customers who bought this also bought
# ---------------------------------------------------------------
st.subheader("Customers Who Bought This Also Bought")
st.caption(
    "From market basket analysis of UK orders. Confidence: the share of orders containing the selected product "
    "that also contain the other product. Lift: how many times more likely the pair is to appear together than "
    "if the two were bought independently (1.0 means no association)."
)

antecedent_options = (rules.groupby("antecedents")["lift"].max()
                      .sort_values(ascending=False).index.tolist())
chosen = st.selectbox(
    "Product bought (products with the strongest associations listed first)",
    antecedent_options,
)

related = rules[rules["antecedents"] == chosen].sort_values(["lift", "confidence"], ascending=False)
related_table = related[["consequents", "confidence", "lift", "support"]].rename(columns={
    "consequents": "Also Bought",
    "confidence": "Confidence",
    "lift": "Lift",
    "support": "Share of All Orders With Both",
})
st.dataframe(
    related_table.style.format({
        "Confidence": "{:.1%}",
        "Lift": "{:.1f}",
        "Share of All Orders With Both": "{:.2%}",
    }),
    use_container_width=True,
    hide_index=True,
)
if not related.empty:
    top = related.iloc[0]
    st.caption(
        f"Reading the top row: {top['confidence']:.0%} of orders containing {chosen} also contain "
        f"{top['consequents']}, {top['lift']:.1f} times the rate expected by chance."
    )

st.divider()

# ---------------------------------------------------------------
# 4. Products by customer segment
# ---------------------------------------------------------------
st.subheader("What Each Segment Buys")
st.caption(
    "Revenue from customers in the selected segment (customers with a segment from clustering). "
    "\"Segment's share\" is how much of the product's revenue, across all segments, comes from this segment."
)

segment_options = (by_segment.groupby("Segment_Name")["Revenue"].sum()
                   .sort_values(ascending=False).index.tolist())
col_g1, col_g2 = st.columns([2, 1])
chosen_segment = col_g1.selectbox("Segment", segment_options)
seg_top_n = col_g2.slider("How many products", 5, 30, 10, 5)

product_totals = by_segment.groupby(["StockCode", "Description"])["Revenue"].sum().rename("All_Segments_Revenue")
seg = (by_segment[by_segment["Segment_Name"] == chosen_segment]
       .merge(product_totals.reset_index(), on=["StockCode", "Description"]))
seg["Segment_Share"] = seg["Revenue"] / seg["All_Segments_Revenue"]
seg = seg.sort_values("Revenue", ascending=False).head(seg_top_n)

fig_seg = px.bar(
    seg.iloc[::-1], x="Revenue", y="Description", orientation="h",
    color_discrete_sequence=[SEGMENT_COLORS.get(chosen_segment, "#4C78A8")],
    hover_data={"Customers": ":,", "Segment_Share": ":.1%"},
    labels={"Revenue": "Revenue (£)", "Description": "", "Segment_Share": "Segment's share of product revenue"},
)
fig_seg.update_xaxes(tickprefix="£", tickformat=",")
fig_seg.update_layout(height=max(350, 28 * len(seg)))
st.plotly_chart(fig_seg, use_container_width=True)

st.dataframe(
    seg[["Description", "Revenue", "Units", "Customers", "Segment_Share"]].rename(columns={
        "Segment_Share": "Segment's Share of Product Revenue"
    }).style.format({
        "Revenue": "£{:,.0f}",
        "Units": "{:,.0f}",
        "Customers": "{:,.0f}",
        "Segment's Share of Product Revenue": "{:.1%}",
    }),
    use_container_width=True,
    hide_index=True,
)
