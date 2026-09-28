import pandas as pd


def net_cancellations(df, customer_col='Customer ID', product_col='StockCode',
                      invoice_col='Invoice', qty_col='Quantity',
                      price_col='Price', date_col='InvoiceDate',
                      return_log=False):
    """
    Net cancellation lines (invoices starting with 'C') against the purchases they reverse.

    For each cancellation, in chronological order, quantity is removed from the same
    customer's earlier purchases of the same product, most recent first (LIFO).
    Purchases reduced to zero are dropped; cancelled quantity with no earlier purchase
    to net against (original order before the data window) is discarded.

    Returns (netted_sales_df, summary_dict), plus an allocation log DataFrame
    if return_log=True (one row per cancellation-to-purchase allocation).
    """
    is_cancel = df[invoice_col].astype(str).str.startswith('C')
    sales = df[~is_cancel & (df[qty_col] > 0)].copy()
    cancels = df[is_cancel & (df[qty_col] < 0)].sort_values(date_col)

    keys = [customer_col, product_col]

    # Only purchases whose (customer, product) pair was ever cancelled are candidates
    cancel_keys = set(zip(cancels[customer_col], cancels[product_col]))
    sales_keys = pd.Series(list(zip(sales[customer_col], sales[product_col])), index=sales.index)
    candidates = sales[sales_keys.isin(cancel_keys)].sort_values(date_col)

    by_key = {k: list(g.index) for k, g in candidates.groupby(keys, sort=False)}

    remaining = sales[qty_col].to_dict()
    sale_time = candidates[date_col].to_dict()
    sale_price = candidates[price_col].to_dict()
    sale_invoice = candidates[invoice_col].to_dict()

    fully, partly, unmatched = 0, 0, 0
    netted_value, unmatched_value = 0.0, 0.0
    log = []

    for c_idx, c_inv, cust, code, qty, t, c_price in zip(
        cancels.index, cancels[invoice_col], cancels[customer_col], cancels[product_col],
        -cancels[qty_col], cancels[date_col], cancels[price_col]
    ):
        to_cancel = qty
        for s_idx in reversed(by_key.get((cust, code), [])):  # most recent first
            if sale_time[s_idx] > t or remaining[s_idx] <= 0:
                continue
            take = min(remaining[s_idx], to_cancel)
            remaining[s_idx] -= take
            netted_value += take * sale_price[s_idx]
            to_cancel -= take
            if return_log:
                log.append({
                    'Cancel_Invoice': c_inv,
                    'Sale_Invoice': sale_invoice[s_idx],
                    customer_col: cust,
                    product_col: code,
                    'Cancel_Date': t,
                    'Sale_Date': sale_time[s_idx],
                    'Qty': take,
                    'Cancel_Price': c_price,
                    'Sale_Price': sale_price[s_idx],
                })
            if to_cancel == 0:
                break

        if to_cancel == 0:
            fully += 1
        elif to_cancel < qty:
            partly += 1
            unmatched_value += to_cancel * c_price
        else:
            unmatched += 1
            unmatched_value += to_cancel * c_price

    sales[qty_col] = pd.Series(remaining)
    rows_before = len(sales)
    reduced = int((sales[qty_col] < df.loc[sales.index, qty_col]).sum())
    sales = sales[sales[qty_col] > 0]

    summary = {
        'cancellation_lines': len(cancels),
        'fully_netted': fully,
        'partly_netted': partly,
        'unmatched': unmatched,
        'value_netted': round(netted_value, 2),
        'value_unmatched_discarded': round(unmatched_value, 2),
        'purchase_rows_reduced': reduced,
        'purchase_rows_removed_entirely': rows_before - len(sales),
    }

    if return_log:
        return sales, summary, pd.DataFrame(log)
    return sales, summary