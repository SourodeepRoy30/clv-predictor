"""
Plain-language definitions used across the app.

Every tooltip and the Glossary page read from this one dictionary, so each term is defined once
and worded the same way everywhere. "short" is the one-line tooltip; "long" is the Glossary entry.
"""

GLOSSARY = {
    # ---------------- Customer behaviour ----------------
    "Recency": {
        "group": "Customer behaviour",
        "short": "Days since the customer's last purchase. Lower means more recently active.",
        "long": "The number of days between a customer's most recent purchase and the date the snapshot was taken. "
                "A customer who bought last week has low recency; one who has not bought for a year has high recency. "
                "It is the strongest single signal of whether a customer will buy again soon.",
    },
    "Frequency": {
        "group": "Customer behaviour",
        "short": "Number of separate orders the customer placed.",
        "long": "How many separate orders (invoices) a customer placed during the period. Ten orders of £50 and one "
                "order of £500 have the same total spend but very different frequency.",
    },
    "Monetary": {
        "group": "Customer behaviour",
        "short": "Total amount the customer spent during the period.",
        "long": "The customer's total spend during the period, after cancelled orders are removed. Also called "
                "historical spend.",
    },
    "RFM": {
        "group": "Customer behaviour",
        "short": "Recency, Frequency and Monetary: the three classic measures of customer behaviour.",
        "long": "Recency, Frequency and Monetary value, the three classic measures used to describe and segment "
                "customers: how recently they bought, how often, and how much.",
    },
    "Average order value": {
        "group": "Customer behaviour",
        "short": "Total spend divided by the number of orders.",
        "long": "Total spend divided by the number of orders (AOV). It separates customers who place a few large "
                "orders from those who place many small ones.",
    },
    "Tenure": {
        "group": "Customer behaviour",
        "short": "Days since the customer's first purchase.",
        "long": "The number of days between a customer's first purchase and the snapshot date: how long they have "
                "been a customer.",
    },
    "Unique products": {
        "group": "Customer behaviour",
        "short": "Number of different products the customer has bought.",
        "long": "How many different products a customer has bought, a measure of how broadly they shop across the "
                "catalogue.",
    },
    "Days between purchases": {
        "group": "Customer behaviour",
        "short": "Average gap between orders: tenure divided by number of orders.",
        "long": "The customer's tenure divided by their number of orders, a rough measure of their buying rhythm. "
                "For a single-order customer it equals their tenure.",
    },
    "Snapshot": {
        "group": "Customer behaviour",
        "short": "The date up to which a customer's behaviour is measured, before predicting what comes next.",
        "long": "Predictions use a customer's behaviour up to a fixed date (the snapshot) to predict what they do "
                "afterwards. The 6-month model uses behaviour up to 2011-06-08 and predicts 2011-06-09 to "
                "2011-12-09. The 12-month model uses an earlier snapshot, up to 2010-11-30, and predicts "
                "2010-12-01 to 2011-12-09.",
    },

    # ---------------- Predictions ----------------
    "Customer lifetime value": {
        "group": "Predictions",
        "short": "How much a customer is expected to spend over a future period.",
        "long": "Customer lifetime value (CLV) is the revenue a customer is expected to bring in over a future "
                "period. This app predicts it over the next 6 and 12 months. It helps a business decide which "
                "customers are worth investing in to keep.",
    },
    "Churn": {
        "group": "Predictions",
        "short": "A customer who makes no purchase during the prediction period.",
        "long": "A customer has churned if they make no purchase at all during the prediction period. There is no "
                "subscription to cancel in retail, so churn is defined by inactivity.",
    },
    "Churn risk": {
        "group": "Predictions",
        "short": "The model's estimated probability that the customer makes no purchase in the period.",
        "long": "The model's estimated probability that a customer will make no purchase during the prediction "
                "period. The label \"Likely to Churn\" is shown when it is 50% or higher. It is an estimate, not a "
                "certainty: see Calibration on the Model Info page for how closely these probabilities match reality.",
    },
    "Spend if retained": {
        "group": "Predictions",
        "short": "Predicted spend if the customer does buy again.",
        "long": "The predicted amount a customer spends during the period, assuming they do buy again. It comes from "
                "a model trained only on customers who returned.",
    },
    "Expected CLV": {
        "group": "Predictions",
        "short": "Spend if retained, weighted by the chance the customer returns: (1 - churn risk) x spend if retained.",
        "long": "The app's CLV prediction: spend if retained multiplied by the probability the customer returns. "
                "For example, a customer with a 30% churn risk who would spend £1,000 if retained has an expected "
                "CLV of £700. Across many customers, these predictions add up to the revenue actually expected.",
    },
    "Value at risk": {
        "group": "Predictions",
        "short": "Revenue expected to be lost to churn: churn risk x spend if retained.",
        "long": "The revenue expected to be lost if a customer churns: churn risk multiplied by spend if retained. "
                "Expected CLV and value at risk always add up to spend if retained. Ranking customers by value at "
                "risk puts valuable customers who might leave at the top of a retention list.",
    },
    "Two-stage model": {
        "group": "Predictions",
        "short": "One model predicts whether a customer returns, a second predicts how much they spend.",
        "long": "A model built in two parts: Stage 1 predicts whether a customer will buy again (churn risk), and "
                "Stage 2 predicts how much a returning customer will spend. Splitting the question this way handles "
                "the many customers who spend nothing, and guarantees predictions are never negative.",
    },

    # ---------------- Retention planning ----------------
    "Net benefit": {
        "group": "Retention planning",
        "short": "Expected revenue saved by contacting a customer, minus the cost of contacting them.",
        "long": "The expected gain from contacting a customer: retention success rate x value at risk, minus the "
                "cost per contact. Contacting a customer is worthwhile only when this is positive.",
    },
    "Retention success rate": {
        "group": "Retention planning",
        "short": "Share of at-risk customers a retention campaign is assumed to win back.",
        "long": "The share of customers who would otherwise churn that a retention campaign wins back. The app's "
                "default (20%) is a placeholder to be replaced with a real campaign's figure.",
    },
    "Cost per contact": {
        "group": "Retention planning",
        "short": "What it costs to contact one customer, for example a discount or staff time.",
        "long": "The cost of contacting one customer in a retention campaign: an email, a call, a discount voucher. "
                "The app's default (£5) is a placeholder.",
    },

    # ---------------- Segments ----------------
    "Segment": {
        "group": "Segments",
        "short": "A group of customers with similar recency, frequency and spend, found by clustering.",
        "long": "Customers are grouped into four segments by K-Means clustering on recency, frequency and spend. "
                "Most customers lie on a continuous spectrum, so the boundaries between the two large segments "
                "are an approximation rather than a sharp divide.",
    },
    "Elite Wholesalers": {
        "group": "Segments",
        "short": "A handful of customers with extremely high order counts and spend.",
        "long": "Five customers with extremely high order counts and spend (about £260,000 each on average). They "
                "buy a noticeably different mix of products from everyone else.",
    },
    "High-Value Regulars": {
        "group": "Segments",
        "short": "Frequent, recent, high-spending customers: about 1% of customers.",
        "long": "About 50 customers who buy often and recently and spend heavily (about £39,000 each on average). "
                "Together with the Elite Wholesalers they are about 1% of customers but nearly 29% of revenue.",
    },
    "Typical Steady": {
        "group": "Segments",
        "short": "The active core of the customer base: about half of all customers.",
        "long": "About half of all customers: still active, buying a few times, with moderate spend. As the largest "
                "group, they bring in the most revenue overall.",
    },
    "At-Risk/Lapsed": {
        "group": "Segments",
        "short": "Customers who have not bought for a long time: nearly half of all customers.",
        "long": "Nearly half of all customers: they have bought only a couple of times and not for many months "
                "(about 10 months on average). The natural target for re-engagement campaigns.",
    },

    # ---------------- Products ----------------
    "Revenue per order": {
        "group": "Products",
        "short": "A product's total revenue divided by the number of orders it appeared in.",
        "long": "A product's total revenue divided by the number of orders containing it. High values point to "
                "high-value items such as furniture.",
    },
    "Single-order driven": {
        "group": "Products",
        "short": "A product (with £5,000+ revenue) where one order supplies half or more of its revenue.",
        "long": "A product with at least £5,000 of revenue where a single order supplies half or more of it. Its "
                "revenue rank reflects one large purchase rather than broad demand.",
    },
    "Largest order's share": {
        "group": "Products",
        "short": "The share of a product's revenue that came from its single biggest order.",
        "long": "The share of a product's total revenue that came from its single largest order. Low values mean "
                "demand is spread across many orders.",
    },
    "Confidence": {
        "group": "Products",
        "short": "Share of orders containing the first product that also contain the second.",
        "long": "In \"customers who bought X also bought Y\": the share of orders containing X that also contain Y. "
                "It is directional, so X to Y and Y to X usually differ.",
    },
    "Lift": {
        "group": "Products",
        "short": "How many times more often two products are bought together than chance would predict.",
        "long": "How many times more often two products appear in the same order than if they were bought "
                "independently. A lift of 1 means no association; a lift of 50 means 50 times more likely than "
                "chance, typical of items from a matching set.",
    },
    "Support": {
        "group": "Products",
        "short": "Share of all orders containing both products.",
        "long": "The share of all orders that contain both products. Low support with high lift means a strong but "
                "niche association.",
    },

    # ---------------- Model evaluation ----------------
    "ROC-AUC": {
        "group": "Model evaluation",
        "short": "How well the churn model ranks customers: 0.5 is a coin flip, 1.0 is perfect.",
        "long": "The probability that the model gives a randomly chosen churner a higher churn risk than a randomly "
                "chosen active customer. 0.5 is no better than a coin flip; 1.0 is perfect. The churn models here "
                "reach about 0.80.",
    },
    "MAE": {
        "group": "Model evaluation",
        "short": "Mean absolute error: the average size of a prediction's miss, in pounds.",
        "long": "Mean absolute error: the average difference, in pounds, between predicted and actual spend. Lower "
                "is better.",
    },
    "RMSE": {
        "group": "Model evaluation",
        "short": "Root mean squared error: like MAE, but large misses count much more.",
        "long": "Root mean squared error: like MAE, but errors are squared before averaging, so a few large misses "
                "weigh heavily. Lower is better.",
    },
    "R-squared": {
        "group": "Model evaluation",
        "short": "Share of the variation in actual spend that the model explains.",
        "long": "The share of the variation in actual spend explained by the model: 0 means no better than "
                "predicting the average for everyone, 1 means perfect.",
    },
    "Out-of-fold": {
        "group": "Model evaluation",
        "short": "Scores from cross-validation: each customer predicted by a model that never saw them.",
        "long": "A cross-validation score: the training customers are split into five parts, and each part is "
                "predicted by a model trained on the other four. Every customer is predicted by a model that never "
                "saw them, which gives a reliable basis for choosing between models.",
    },
    "Test set": {
        "group": "Model evaluation",
        "short": "Customers held back from training and used once for a final check.",
        "long": "A fifth of customers held back from all training and model selection, and used once for a final "
                "check of the chosen model.",
    },
    "Calibration": {
        "group": "Model evaluation",
        "short": "Whether predicted probabilities match reality: of customers given 70%, do about 70% churn?",
        "long": "Whether predicted probabilities can be taken at face value: of all customers given a 70% churn "
                "risk, roughly 70% should actually churn. Shown on the Model Info page.",
    },
    "Predicted / actual total": {
        "group": "Model evaluation",
        "short": "Total predicted revenue divided by total actual revenue; 100% means the totals match.",
        "long": "Total predicted revenue divided by total actual revenue. Close to 100% means the predictions add "
                "up to the right total, which matters when CLV is used for planning.",
    },
    "Cancellation netting": {
        "group": "Model evaluation",
        "short": "Removing purchases that were later cancelled, so they don't count as revenue.",
        "long": "Cancelled orders are offset against the purchases they reversed (most recent first), so revenue "
                "that was never received is not counted. Without this, two orders cancelled within minutes "
                "(£77,184 and £168,470) would have counted as genuine spend.",
    },
}

GROUP_ORDER = ["Predictions", "Customer behaviour", "Retention planning", "Segments", "Products", "Model evaluation"]


def tip(term):
    """One-line tooltip text for a glossary term."""
    return GLOSSARY[term]["short"]
