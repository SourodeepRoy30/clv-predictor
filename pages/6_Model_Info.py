import streamlit as st
import sys
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, brier_score_loss, mean_absolute_error, r2_score
from sklearn.calibration import calibration_curve

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import load_models, load_data, load_configs, FEATURE_COLS, predict_clv, describe_config, by_customer_id
from definitions import tip
from ui import page_header, prediction_flowchart, flowchart_example, DEFAULT_CUSTOMER

page_header(
    "Model Info",
    "Can these predictions be trusted?",
    how_to="""
**What this page shows:** how the predictions are made, how accurate they are on customers the models never saw during training, and where they fall short.

**The four tabs:**
- **How it works:** the two-stage model behind every prediction in the app.
- **Performance:** accuracy figures, recalculated live from the saved models.
- **Reliability:** whether a predicted churn risk of, say, 70% really means about 70% of such customers stop buying.
- **Limitations:** what to keep in mind when reading the predictions.
""",
)

models = load_models()
configs = load_configs()
data = load_data()

HORIZONS = {
    "6mo": {"label": "6 months", "table": "modeling_table",
            "period": "Behaviour to 2011-06-08, predicting 2011-06-09 to 2011-12-09"},
    "12mo": {"label": "12 months", "table": "modeling_table_12mo",
             "period": "Behaviour to 2010-11-30, predicting 2010-12-01 to 2011-12-09"},
}


@st.cache_data
def test_set_results(_models, _configs, horizon, table):
    """Recreate the notebooks' test split (test_size=0.2, random_state=42, stratified on churn) and score it."""
    churned = (table["CLV_Target"] == 0).astype(int)
    _, X_test, _, churned_test, _, clv_test = train_test_split(
        table[FEATURE_COLS], churned, table["CLV_Target"], test_size=0.2, random_state=42, stratify=churned)
    preds = predict_clv(_models, _configs, horizon, X_test)
    return churned_test.values, preds["Churn_Prob"].values, clv_test.values, preds["Expected_CLV"].values


results = {h: test_set_results(models, configs, h, data[info["table"]]) for h, info in HORIZONS.items()}
auc_6 = roc_auc_score(results["6mo"][0], results["6mo"][1])

st.info(
    f"The 6-month churn model ranks customers correctly about **{auc_6:.0%} of the time** (given one customer who "
    f"stopped buying and one who did not, it gives the first a higher risk), and its predicted revenue adds up to "
    f"**{configs['clv_6mo']['test_pred_actual_total']:.0%}** of actual revenue on unseen customers. Good enough to "
    "rank and prioritise customers; individual predictions are estimates, not certainties.",
    icon=":material/verified:",
)

tab_how, tab_perf, tab_rel, tab_limits = st.tabs(["How it works", "Performance", "Reliability", "Limitations"])


# How it works
with tab_how:
    prediction_flowchart("flow_model_info",
                         example=flowchart_example(models, configs, by_customer_id(data["modeling_table"]),
                                                   DEFAULT_CUSTOMER))
    for h, info in HORIZONS.items():
        st.markdown(f"**Next {info['label']}:** {describe_config(configs[f'clv_{h}'])}. :gray[{info['period']}.]")

    with st.expander("Why this design was chosen"):
        st.markdown(
            "- **Two stages:** nearly half of customers spend nothing in the period. A single model has to handle "
            "that pile of zeros and the size of spend at the same time; splitting the question handles both, and "
            "guarantees predictions are never negative.\n"
            "- **Expected value rather than a cut-off:** a rule predicting £0 for every customer above a churn "
            "threshold had a slightly lower average error, but its predictions added up to only about 79% of actual "
            "revenue, and it could not rank customers above the threshold. The expected value rule adds up to "
            "about 100% and ranks every customer.\n"
            "- **Chosen by cross-validation:** every option was scored on customers the model had not seen, using "
            "five rounds of training and testing on the training data. The final held-out test set was used once, "
            "only to check the chosen model.\n"
            "- **Segments** come from K-Means clustering on recency, frequency and spend, with names assigned by "
            "rule from each cluster's profile."
        )


# Performance
with tab_perf:
    st.caption("Measured on a held-out test set: a fifth of customers that played no part in training. The app "
               "recreates that test set and rescores the saved models, so these numbers are calculated live.")
    for h, info in HORIZONS.items():
        churned_test, churn_prob, clv_test, clv_pred = results[h]
        cfg = configs[f"clv_{h}"]
        live_mae = mean_absolute_error(clv_test, clv_pred)
        matches = abs(live_mae - cfg["test_mae"]) < 0.01
        with st.container(border=True):
            badge = ":green-badge[:material/check: Matches the notebook]" if matches else \
                ":red-badge[:material/close: Differs from the notebook]"
            st.markdown(f"**Next {info['label']}** &nbsp; {badge}")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Churn ranking (ROC-AUC)", f"{roc_auc_score(churned_test, churn_prob):.3f}", help=tip("ROC-AUC"))
            m2.metric("Average error (MAE)", f"£{live_mae:,.0f}", help=tip("MAE"))
            m3.metric("Variation explained (R²)", f"{r2_score(clv_test, clv_pred):.2f}", help=tip("R-squared"))
            m4.metric("Predicted / actual total", f"{cfg['test_pred_actual_total']:.0%}",
                      help=tip("Predicted / actual total"))
            st.caption(f"{len(clv_test):,} test customers. Cross-validated average error across the training "
                       f"customers, the figure the model was chosen on: £{cfg['oof_mae']:,.0f}.")
    with st.expander("Why are there two kinds of score?"):
        st.write(
            "Spend is very uneven: a few customers spend hundreds of times more than most. A single test set of "
            "under 1,000 customers can therefore look better or worse depending on which big spenders it happens "
            "to contain. The cross-validated score averages over all training customers and is the more reliable "
            "basis for choosing a model; the test set gives one final, independent check."
        )

# Reliability
with tab_rel:
    horizon_label = st.segmented_control("Horizon", [f"Next {i['label']}" for i in HORIZONS.values()],
                                         default="Next 6 months", key="calibration_horizon") or "Next 6 months"
    h = next(k for k, v in HORIZONS.items() if f"Next {v['label']}" == horizon_label)
    churned_test, churn_prob, _, _ = results[h]

    observed, predicted = calibration_curve(churned_test, churn_prob, n_bins=10, strategy="quantile")
    gaps = observed - predicted
    brier = brier_score_loss(churned_test, churn_prob)
    base_rate = churned_test.mean()
    brier_baseline = base_rate * (1 - base_rate)

    chart_col, text_col = st.columns([3, 2], gap="large")
    with chart_col:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfectly reliable",
                                 line=dict(dash="dash", color="#9AA0AC")))
        fig.add_trace(go.Scatter(x=predicted, y=observed, mode="lines+markers", name="This model",
                                 marker=dict(size=9, color="#3A6EA5"), line=dict(color="#3A6EA5"),
                                 hovertemplate="Predicted: %{x:.0%}<br>Actually stopped buying: %{y:.0%}<extra></extra>"))
        fig.update_layout(height=430, legend=dict(orientation="h", y=-0.2),
                          xaxis=dict(title="Predicted churn risk", tickformat=".0%", range=[0, 1]),
                          yaxis=dict(title="Share who actually stopped buying", tickformat=".0%", range=[0, 1]))
        st.plotly_chart(fig, width="stretch")
    with text_col:
        st.markdown("**How to read this**")
        st.caption("Test customers are split into ten equal groups by predicted risk. Each point compares a group's "
                   "average prediction with the share that actually stopped buying. Points on the dashed line mean "
                   "the predictions can be taken at face value.")
        st.metric("Average gap from the line", f"{np.mean(np.abs(gaps)) * 100:.1f} points",
                  help="Mean absolute difference between predicted and actual churn across the ten groups.",
                  border=True)
        st.metric("Prediction error (Brier score)", f"{brier:.3f}",
                  f"vs {brier_baseline:.3f} guessing the average rate", delta_color="off", delta_arrow="off",
                  help="Mean squared error of the probabilities. Lower is better; beating the second number shows "
                       "the predictions carry real information.", border=True)
    direction = "underestimates" if gaps[-3:].mean() > 0 else "overestimates"
    st.caption(f"Predicted risks range from {churn_prob.min():.0%} to {churn_prob.max():.0%}, so the model never "
               f"treats a customer as nearly certain to stay or to leave. Among the highest-risk customers it "
               f"{direction} churn on average.")

# Limitations
with tab_limits:
    LIMITS = [
        (":material/exposure_zero:", "Some spend predictions show £0",
         "For some low-value, long-lapsed customers the spend model's estimate falls below zero and is shown as £0. "
         "Read these as \"very low\"."),
        (":material/trending_up:", "Very large orders are extrapolated",
         "The spend model scales up a customer's average order value, so one or two unusually large orders can "
         "produce a forecast above their past spend."),
        (":material/compress:", "Churn risks stay in a middle range",
         "Predicted risks never approach 0% or 100%. The Reliability tab shows how closely they match reality."),
        (":material/shuffle:", "Test results vary with the sample",
         "Spend is very uneven across customers, so test-set figures depend on which big spenders are included. "
         "Models were chosen on cross-validated results instead."),
        (":material/speed:", "A ceiling of about 0.80 for churn",
         "Nine algorithms and extended tuning all reached roughly the same accuracy, which points to the limits of "
         "the seven behavioural measures rather than of the modelling."),
        (":material/history:", "The 12-month model uses an older snapshot",
         "It sees behaviour up to November 2010 and customers with at most a year of history."),
        (":material/calendar_month:", "Days are calendar days",
         "Store closures, such as about 12 days over Christmas, make some customers look slightly more lapsed than "
         "their trading-day gap would suggest."),
        (":material/remove_shopping_cart:", "Cancelled orders are removed",
         "Purchases later cancelled are netted out. Pricing or entry errors that were never cancelled remain."),
        (":material/person_add:", "New customers cannot be scored",
         "A model using only first-order details was tested and not deployed: it explained under 5% of the "
         "variation in 90-day spend and did not beat simple baselines."),
    ]
    for row_start in range(0, len(LIMITS), 3):
        for col, (icon, title, text) in zip(st.columns(3), LIMITS[row_start:row_start + 3]):
            with col.container(border=True, height="stretch"):
                st.markdown(f"**{icon} {title}**")
                st.caption(text)
