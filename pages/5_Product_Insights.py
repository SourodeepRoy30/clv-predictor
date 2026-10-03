import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import load_data, SEGMENT_COLORS
from definitions import tip
from ui import page_header

page_header(
    "Product Insights",
    "What sells, when, and with what?",
    how_to="""
**What this page shows:** product performance from all cleaned transactions (December 2009 to December 2011, with cancelled orders removed).

**The four tabs:**
- **Top products:** rank products by revenue, units, orders or revenue per order. Red bars mark products whose revenue rests on a single large order.
- **Seasonality:** monthly sales for products you choose. Switch to *share of the product's total* to compare the shape of products of very different sizes.
- **Bought together:** pick a product to see what is most often bought with it (UK orders).
- **By segment:** what each customer segment buys, and how much of each product's revenue comes from that segment.
""",
)

data = load_data()
products = data["product_summary"]
monthly = data["product_monthly"]
rules = data["association_rules"]
by_segment = data["product_segment"]


# Summary
best = products.sort_values("Total_Revenue", ascending=False).iloc[0]
top10 = products.sort_values("Total_Revenue", ascending=False).head(10)
st.info(
    f"**{best['Description'].title()}** is the top product (£{best['Total_Revenue']:,.0f} across "
    f"{best['Order_Count']:,} orders). Every top-10 product sells across hundreds of separate orders, the largest "
    f"single order never supplying more than {top10['Top_Order_Share'].max():.0%} of a top-10 product's revenue. "
    f"{int(products['Is_Outlier_Driven'].sum())} smaller products owe half or more of their revenue to one order.",
    icon=":material/lightbulb:",
)

tab_top, tab_season, tab_together, tab_segment = st.tabs(
    ["Top products", "Seasonality", "Bought together", "By segment"])


# Top products
with tab_top:
    RANK_OPTIONS = {"Revenue": "Total_Revenue", "Units sold": "Total_Units_Sold",
                    "Orders": "Order_Count", "Revenue per order": "Revenue_Per_Order"}
    c1, c2, c3 = st.columns([3, 2, 2], vertical_alignment="bottom")
    rank_label = c1.segmented_control("Rank by", list(RANK_OPTIONS), default="Revenue", key="rank_by") or "Revenue"
    top_n = c2.slider("How many", 5, 50, 15, 5)
    hide_flagged = c3.toggle("Hide single-order-driven", help=tip("Single-order driven"))

    ranked = products.copy()
    if rank_label == "Revenue per order":
        ranked = ranked[ranked["Order_Count"] >= 5]
    if hide_flagged:
        ranked = ranked[~ranked["Is_Outlier_Driven"]]
    ranked = ranked.sort_values(RANK_OPTIONS[rank_label], ascending=False).head(top_n)
    ranked["Bar"] = ranked["Is_Outlier_Driven"].map({True: "Single-order driven", False: "Broad demand"})

    fig = px.bar(ranked.iloc[::-1], x=RANK_OPTIONS[rank_label], y="Description", orientation="h", color="Bar",
                 color_discrete_map={"Broad demand": "#3A6EA5", "Single-order driven": "#D9534F"},
                 hover_data={"Total_Revenue": ":,.0f", "Order_Count": ":,", "Top_Order_Share": ":.1%", "Bar": False},
                 labels={RANK_OPTIONS[rank_label]: rank_label, "Description": "", "Total_Revenue": "Revenue (£)",
                         "Order_Count": "Orders", "Top_Order_Share": "Largest order's share"})
    fig.update_layout(height=max(360, 28 * len(ranked)), legend=dict(title_text="", orientation="h", y=1.05))
    if rank_label in ("Revenue", "Revenue per order"):
        fig.update_xaxes(tickprefix="£", tickformat=",")
    st.plotly_chart(fig, width="stretch")
    if rank_label == "Revenue per order":
        st.caption("Only products with at least 5 orders, so a single large order cannot top the ranking by chance.")

    with st.expander("Show as a table"):
        st.dataframe(
            ranked[["Description", "Total_Revenue", "Total_Units_Sold", "Order_Count", "Revenue_Per_Order",
                    "Top_Order_Share"]].style.format({"Total_Revenue": "£{:,.0f}", "Total_Units_Sold": "{:,.0f}",
                                                      "Order_Count": "{:,.0f}", "Revenue_Per_Order": "£{:,.2f}"}),
            width="stretch", hide_index=True,
            column_config={
                "Description": "Product", "Total_Revenue": "Revenue", "Total_Units_Sold": "Units sold",
                "Order_Count": "Orders",
                "Revenue_Per_Order": st.column_config.Column("Revenue per order", help=tip("Revenue per order")),
                "Top_Order_Share": st.column_config.ProgressColumn("Largest order's share", min_value=0, max_value=1,
                                                                   format="percent", help=tip("Largest order's share")),
            },
        )


# Seasonality
with tab_season:
    all_months = sorted(monthly["Month"].unique())
    product_options = products.sort_values("Total_Revenue", ascending=False)["Description"].tolist()
    # Default: the top three products plus a clearly seasonal one, if present, to show the contrast
    seasonal = [p for p in product_options if p.strip().upper().startswith("PAPER CHAIN KIT 50")][:1]
    default = product_options[:3] + [p for p in seasonal if p not in product_options[:3]]

    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    selected = c1.multiselect("Products", product_options, default=default, max_selections=8,
                              placeholder="Type to search products")
    as_share = c2.segmented_control("Show", ["Revenue", "Share of product's total"], default="Revenue",
                                    key="season_view") == "Share of product's total"

    if selected:
        season = monthly[monthly["Description"].isin(selected)].groupby(["Description", "Month"],
                                                                        as_index=False)["Revenue"].sum()
        grid = pd.MultiIndex.from_product([selected, all_months], names=["Description", "Month"])
        season = season.set_index(["Description", "Month"]).reindex(grid, fill_value=0).reset_index()
        y_col = "Revenue"
        if as_share:
            season["Share"] = season["Revenue"] / season.groupby("Description")["Revenue"].transform("sum")
            y_col = "Share"
        fig = px.line(season, x="Month", y=y_col, color="Description", markers=True,
                      labels={"Revenue": "Revenue", "Share": "Share of the product's revenue", "Description": "",
                              "Month": ""})
        fig.update_yaxes(tickformat=".0%" if as_share else ",", tickprefix="" if as_share else "£")
        fig.add_vrect(x0=all_months[-2], x1=all_months[-1], fillcolor="gray", opacity=0.15, line_width=0,
                      annotation_text="partial month", annotation_position="top left")
        fig.update_layout(height=480, legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")
        st.caption("Months without sales count as zero. December 2011 is partial: the data ends on the 9th.")
    else:
        st.info("Choose at least one product.", icon=":material/info:")


# Bought together
with tab_together:
    options = rules.groupby("antecedents")["lift"].max().sort_values(ascending=False).index.tolist()
    chosen = st.selectbox("When a customer buys", options,
                          help="Products with the strongest associations are listed first. Type to search.")
    related = rules[rules["antecedents"] == chosen].sort_values(["lift", "confidence"], ascending=False)
    if not related.empty:
        lead = related.iloc[0]
        st.success(f"**{lead['confidence']:.0%}** of orders containing *{chosen.strip().title()}* also contain "
                   f"*{lead['consequents'].strip().title()}*, **{lead['lift']:.0f} times** as often as chance "
                   "would predict.", icon=":material/shopping_basket:")
    st.dataframe(
        related[["consequents", "confidence", "lift", "support"]],
        width="stretch", hide_index=True,
        column_config={
            "consequents": "They also buy",
            "confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="percent",
                                                          help=tip("Confidence")),
            "lift": st.column_config.NumberColumn("Lift", format="%.1f", help=tip("Lift")),
            "support": st.column_config.NumberColumn("Support", format="percent", help=tip("Support")),
        },
    )
    st.caption("Based on UK orders with at least two different products.")


# By segment
with tab_segment:
    segment_options = by_segment.groupby("Segment_Name")["Revenue"].sum().sort_values(ascending=False).index.tolist()
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    default_seg = "Elite Wholesalers" if "Elite Wholesalers" in segment_options else segment_options[0]
    chosen_segment = c1.segmented_control("Segment", segment_options, default=default_seg,
                                          key="product_segment") or default_seg
    seg_top_n = c2.slider("Products", 5, 30, 10, 5, key="seg_top_n")

    totals = by_segment.groupby(["StockCode", "Description"])["Revenue"].sum().rename("All_Revenue").reset_index()
    seg = by_segment[by_segment["Segment_Name"] == chosen_segment].merge(totals, on=["StockCode", "Description"])
    seg["Segment_Share"] = seg["Revenue"] / seg["All_Revenue"]
    seg = seg.sort_values("Revenue", ascending=False).head(seg_top_n)

    fig = px.bar(seg.iloc[::-1], x="Revenue", y="Description", orientation="h",
                 color_discrete_sequence=[SEGMENT_COLORS.get(chosen_segment, "#3A6EA5")],
                 hover_data={"Customers": ":,", "Segment_Share": ":.1%"},
                 labels={"Revenue": "Revenue from this segment", "Description": "",
                         "Segment_Share": "Segment's share of product revenue"})
    fig.update_xaxes(tickprefix="£", tickformat=",")
    fig.update_layout(height=max(360, 28 * len(seg)))
    st.plotly_chart(fig, width="stretch")

    st.dataframe(
        seg[["Description", "Revenue", "Customers", "Segment_Share"]].style.format({"Revenue": "£{:,.0f}"}),
        width="stretch", hide_index=True,
        column_config={
            "Description": "Product",
            "Customers": "Customers who bought it",
            "Segment_Share": st.column_config.ProgressColumn(
                "Segment's share of product revenue", min_value=0, max_value=1, format="percent",
                help="How much of the product's revenue, across all segments, comes from this segment."),
        },
    )
