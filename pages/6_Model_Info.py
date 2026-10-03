import streamlit as st
import sys
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, brier_score_loss, mean_absolute_error, mean_squared_error, r2_score
from sklearn.calibration import calibration_curve

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import load_models, load_data, load_configs, FEATURE_COLS, predict_clv, describe_config

st.title("Model Info")
st.write(
    "How the predictions in this app are produced, how well the models perform on customers they were not "
    "trained on, and where their limits are."
)

models = load_models()
configs = load_configs()
data = load_data()

HORIZONS = {
    "6mo": {"label": "6-Month", "table": "modeling_table",
            "period": "behaviour to 2011-06-08, predicting 2011-06-09 to 2011-12-09"},
    "12mo": {"label": "12-Month", "table": "modeling_table_12mo",
             "period": "behaviour to 2010-11-30, predicting 2010-12-01 to 2011-12-09"},
}


@st.cache_data
def test_set_results(_models, _configs, horizon, table):
    """
    Recreate the notebooks' test split (same rows, test_size=0.2, random_state=42, stratified on churn)
    and score the saved models on it. Returns test-set churn labels, churn probabilities and CLV results.
    """
    X = table[FEATURE_COLS]
    churned = (table["CLV_Target"] == 0).astype(int)
    _, X_test, _, churned_test, _, clv_test = train_test_split(
        X, churned, table["CLV_Target"], test_size=0.2, random_state=42, stratify=churned
    )
    preds = predict_clv(_models, _configs, horizon, X_test)
    return churned_test.values, preds["Churn_Prob"].values, clv_test.values, preds["Expected_CLV"].values


results = {h: test_set_results(models, configs, h, data[info["table"]]) for h, info in HORIZONS.items()}

# ---------------------------------------------------------------
# 1. How predictions are made
# ---------------------------------------------------------------
st.subheader("How Predictions Are Made")
st.write(
    "Each horizon uses a two-stage model. Stage 1 estimates the probability *p* that a customer makes no "
    "purchase in the period (churn). Stage 2, trained only on customers who did buy, estimates how much a "
    "returning customer spends, *s*. The two are combined with the Expected Value rule:"
)
st.latex(r"\text{Expected CLV} = (1 - p)\,s \qquad \text{Value at risk} = p\,s \qquad "
         r"\text{Expected CLV} + \text{Value at risk} = s")
st.caption(
    "The Expected Value rule was chosen over a Hard Cutoff (predicting £0 above a churn threshold) because its "
    "predictions add up to actual total revenue and it can still rank customers above any cutoff. A Hard Cutoff "
    "had a lower per-customer error (MAE), but its predictions summed to only about 79% of actual revenue."
)

cols = st.columns(2)
for col, (h, info) in zip(cols, HORIZONS.items()):
    cfg = configs[f"clv_{h}"]
    with col:
        st.markdown(f"**{info['label']} CLV**")
        st.caption(f"{info['period'].capitalize()}. Model: {describe_config(cfg)}.")
        metrics = pd.DataFrame({
            "Metric": ["Out-of-fold MAE (training set, 5 folds)", "Test MAE", "Test RMSE", "Test R-squared",
                       "Test predicted total / actual total"],
            "Value": [f"£{cfg['oof_mae']:,.2f}", f"£{cfg['test_mae']:,.2f}", f"£{cfg['test_rmse']:,.2f}",
                      f"{cfg['test_r2']:.3f}", f"{cfg['test_pred_actual_total']:.1%}"],
        })
        st.dataframe(metrics, hide_index=True, use_container_width=True)
        st.caption(f"Selected by: {cfg['selected_by']}.")

st.info(
    "Why two kinds of score? The model was chosen using 5-fold cross-validation on the training customers "
    "(out-of-fold scores), and then checked once on a held-out test set. With a heavy-tailed target, a single "
    "test set of under 1,000 customers can rank models very differently depending on which big spenders it "
    "happens to contain, so the out-of-fold scores are the more reliable basis for comparing models."
)

st.divider()

# ---------------------------------------------------------------
# 2. Live check against the notebooks
# ---------------------------------------------------------------
st.subheader("Checking the Saved Models Against the Notebooks")
st.write(
    "The app recreates the notebooks' test split and scores the saved models on it. Matching numbers confirm "
    "that the models and data loaded here are the ones that were validated."
)

check_rows = []
for h, info in HORIZONS.items():
    churned_test, churn_prob, clv_test, clv_pred = results[h]
    cfg = configs[f"clv_{h}"]
    live_mae = mean_absolute_error(clv_test, clv_pred)
    check_rows.append({
        "Horizon": info["label"],
        "Test customers": f"{len(clv_test):,}",
        "Churn ROC-AUC (live)": f"{roc_auc_score(churned_test, churn_prob):.4f}",
        "CLV MAE (live)": f"£{live_mae:,.2f}",
        "CLV MAE (notebook)": f"£{cfg['test_mae']:,.2f}",
        "CLV R-squared (live)": f"{r2_score(clv_test, clv_pred):.3f}",
        "Match": "Yes" if abs(live_mae - cfg["test_mae"]) < 0.01 else "No",
    })
st.dataframe(pd.DataFrame(check_rows), hide_index=True, use_container_width=True)
st.caption("The 6-month churn ROC-AUC reported in 4_classification.ipynb is 0.8275.")

st.divider()

# ---------------------------------------------------------------
# 3. Calibration
# ---------------------------------------------------------------
st.subheader("Are the Churn Probabilities Reliable?")
st.write(
    "A ranking model can order customers well and still give misleading probabilities. Calibration checks the "
    "probabilities themselves: test customers are grouped by predicted churn probability, and each group's "
    "average prediction is compared with the share who actually churned. A well-calibrated model sits on the "
    "diagonal. This matters here because value at risk is churn probability times spend, so it is only as "
    "accurate as the probability."
)

horizon_choice = st.radio("Horizon", [info["label"] for info in HORIZONS.values()], horizontal=True)
h = next(k for k, v in HORIZONS.items() if v["label"] == horizon_choice)
churned_test, churn_prob, _, _ = results[h]

n_bins = 10
observed, predicted = calibration_curve(churned_test, churn_prob, n_bins=n_bins, strategy="quantile")
brier = brier_score_loss(churned_test, churn_prob)
base_rate = churned_test.mean()
brier_baseline = base_rate * (1 - base_rate)   # Brier score of always predicting the base rate

fig_cal = go.Figure()
fig_cal.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfect calibration",
                             line=dict(dash="dash", color="gray")))
fig_cal.add_trace(go.Scatter(x=predicted, y=observed, mode="lines+markers", name=f"{horizon_choice} churn model",
                             marker=dict(size=9),
                             hovertemplate="Average predicted: %{x:.1%}<br>Actually churned: %{y:.1%}<extra></extra>"))
fig_cal.update_layout(
    height=480,
    xaxis=dict(title="Average predicted churn probability", tickformat=".0%", range=[0, 1]),
    yaxis=dict(title="Share who actually churned", tickformat=".0%", range=[0, 1]),
    legend=dict(orientation="h", y=-0.2),
)
st.plotly_chart(fig_cal, use_container_width=True)

largest_gap = np.max(np.abs(observed - predicted))
m1, m2, m3 = st.columns(3)
m1.metric("Brier score", f"{brier:.3f}", help="Mean squared error of the probabilities; lower is better.")
m2.metric("Brier score, always predicting the churn rate", f"{brier_baseline:.3f}")
m3.metric("Largest gap from the diagonal", f"{largest_gap:.1%}")
st.caption(
    f"Each point is one tenth of the {len(churned_test):,} test customers, grouped by predicted probability. "
    f"Predicted probabilities on the test set range from {churn_prob.min():.1%} to {churn_prob.max():.1%}, so the "
    "model never treats a customer as nearly certain to stay or to leave."
)

st.divider()

# ---------------------------------------------------------------
# 4. Segments
# ---------------------------------------------------------------
st.subheader("Customer Segments")
st.write(
    "Segments come from K-Means clustering (k=4) on standardized Recency, Frequency and Monetary value. "
    "K-Means numbers clusters arbitrarily, so names are assigned by rule from each cluster's profile: the two "
    "highest-spending clusters are Elite Wholesalers and High-Value Regulars, and of the other two, the one "
    "with the longer average time since last purchase is At-Risk/Lapsed."
)
clusters = data["clusters"]
segment_profile = (clusters.groupby("Segment_Name")
                   .agg(Customers=("Cluster", "count"), Avg_Recency=("Recency", "mean"),
                        Avg_Frequency=("Frequency", "mean"), Avg_Monetary=("Monetary", "mean"))
                   .sort_values("Avg_Monetary", ascending=False))
st.dataframe(
    segment_profile.rename(columns={"Avg_Recency": "Avg Recency (days)", "Avg_Frequency": "Avg Orders",
                                    "Avg_Monetary": "Avg Spend"})
    .style.format({"Customers": "{:,}", "Avg Recency (days)": "{:.1f}", "Avg Orders": "{:.1f}",
                   "Avg Spend": "£{:,.0f}"}),
    use_container_width=True,
)
st.caption(
    "Clustering diagnostics (DBSCAN, hierarchical clustering) showed that most customers lie on a continuous "
    "spectrum, so the boundaries between the two large segments are a useful approximation rather than a sharp divide."
)

st.divider()

# ---------------------------------------------------------------
# 5. Known limitations
# ---------------------------------------------------------------
st.subheader("Known Limitations")
st.markdown("""
- **Some customers show a spend-if-retained of £0.** Stage 2 for the 6-month model is a linear regression. For some low-value, long-lapsed customers it predicts a negative amount, which is shown as £0. Read these as "very low", not literally zero.
- **Extreme order values are extrapolated.** A linear Stage 2 scales up a customer's average order value. Customers with one or two unusually large orders can receive forecasts larger than their past spend, so the top of the At-Risk list deserves a sanity check.
- **Churn probabilities are compressed.** They stay within a middle range rather than approaching 0% or 100%. The calibration chart above shows how closely they match observed churn rates.
- **Single test sets are unstable on this data.** CLV is heavy-tailed, so test metrics move a lot depending on which large spenders the test set contains. Model choices were therefore made on cross-validated results.
- **The ceiling on churn prediction is about 0.80 ROC-AUC.** Nine algorithms and expanded hyperparameter searches all landed close to this level, which points to the limits of the seven behavioural features rather than of the modelling.
- **The 12-month model uses an earlier snapshot** (behaviour up to 2010-11-30) and was trained on customers with at most a year of history, so the What If Simulator warns when Tenure exceeds 365 days.
- **Recency is counted in calendar days**, so store closures (about 12 days over Christmas) make some customers look slightly more lapsed than their trading-day gap would suggest.
- **Cancelled orders are netted out** against the purchases they reversed. Pricing or entry errors that were never cancelled remain in the data.
- **New customers cannot be scored.** A model using only first-order details was tested and not deployed: it explained under 5% of the variation in 90-day spend and did not beat simple baselines.
""")
