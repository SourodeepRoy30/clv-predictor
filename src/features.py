import pandas as pd

def compute_rfm(df, customer_col='Customer ID', invoice_col='Invoice',
                 date_col='InvoiceDate', revenue_col='Revenue', reference_date=None):
    """
    Computes an RFM (Recency, Frequency, Monetary) feature table from
    transaction-level data.

    Parameters:
        df (DataFrame): transaction-level data, one row per line item
        customer_col (str): column identifying each customer
        invoice_col (str): column identifying each order/invoice
        date_col (str): column with transaction datetime
        revenue_col (str): column with per-row revenue (Quantity * Price)
        reference_date (Timestamp): the date Recency is measured against.
            If None, defaults to one day after the dataset's latest transaction.

    Returns:
        DataFrame indexed by customer_col, with Recency, Frequency, Monetary columns.
    """
    if reference_date is None:
        reference_date = (df[date_col].max() + pd.Timedelta(days=1)).normalize()

    recency = (reference_date - df.groupby(customer_col)[date_col].max()).dt.days
    frequency = df.groupby(customer_col)[invoice_col].nunique()
    monetary = df.groupby(customer_col)[revenue_col].sum()

    return pd.DataFrame({
        'Recency': recency,
        'Frequency': frequency,
        'Monetary': monetary
    })
