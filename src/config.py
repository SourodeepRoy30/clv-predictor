# File paths
RAW_DATA_PATH = "../data/online_retail_II.xlsx"
CLEAN_DATA_PATH = "../data/online_retail_clean.csv"
RFM_DATA_PATH = "../data/rfm_table.csv"
MODELING_DATA_PATH = "../data/modeling_table.csv"

# Non-product StockCode values (administrative/adjustment entries, not real merchandise)
NON_PRODUCT_CODES = ["POST", "M", "C2", "BANK CHARGES", "DOT", "D"]

# Column name constants
CUSTOMER_ID_COL = "Customer ID"
INVOICE_COL = "Invoice"
INVOICE_DATE_COL = "InvoiceDate"
QUANTITY_COL = "Quantity"
PRICE_COL = "Price"
STOCKCODE_COL = "StockCode"
COUNTRY_COL = "Country"
REVENUE_COL = "Revenue"
