"""Load and clean the UCI Online Retail II transactions.

Dataset columns: Invoice, StockCode, Description, Quantity, InvoiceDate,
Price, Customer ID, Country. Invoices starting with "C" are cancellations.
"""
from pathlib import Path

import pandas as pd

from . import config

COLUMN_MAP = {"Customer ID": "CustomerID", "Customer_ID": "CustomerID",
              "InvoiceNo": "Invoice", "UnitPrice": "Price"}


def load_raw(path: Path = config.RAW_FILE) -> pd.DataFrame:
    """Read the workbook (all sheets stacked) or a CSV export."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Download Online Retail II from "
            "https://archive.ics.uci.edu/dataset/502/online+retail+ii "
            "and place it in the data/ folder."
        )
    if path.suffix.lower() in {".xlsx", ".xls"}:
        sheets = pd.read_excel(path, sheet_name=None, dtype={"Invoice": str, "StockCode": str})
        df = pd.concat(sheets.values(), ignore_index=True)
    else:
        df = pd.read_csv(path, dtype={"Invoice": str, "StockCode": str},
                         encoding="ISO-8859-1")
    return df.rename(columns=COLUMN_MAP)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return (sales, cancellations, cleaning_log).

    sales          completed product purchases by identified customers
    cancellations  returned/cancelled lines, kept to compute a return rate
    cleaning_log   row counts removed at each step, for the report
    """
    log = {"raw_rows": len(df)}
    df = df.copy()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Invoice"] = df["Invoice"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip()

    before = len(df)
    df = df.drop_duplicates()
    log["duplicates_removed"] = before - len(df)

    before = len(df)
    df = df.dropna(subset=["CustomerID"])
    log["missing_customer_removed"] = before - len(df)
    df["CustomerID"] = df["CustomerID"].astype(float).astype(int)

    before = len(df)
    df = df[~df["StockCode"].isin(config.NON_PRODUCT_CODES)]
    log["non_product_removed"] = before - len(df)

    is_cancel = df["Invoice"].str.startswith("C")
    cancellations = df[is_cancel].copy()
    log["cancellation_rows"] = int(is_cancel.sum())
    df = df[~is_cancel]

    before = len(df)
    df = df[(df["Quantity"] > 0) & (df["Price"] > 0)]
    log["nonpositive_qty_or_price_removed"] = before - len(df)

    df["Revenue"] = df["Quantity"] * df["Price"]
    cancellations["Revenue"] = cancellations["Quantity"].abs() * cancellations["Price"]

    log["clean_rows"] = len(df)
    log["customers"] = df["CustomerID"].nunique()
    log["invoices"] = df["Invoice"].nunique()
    log["date_min"] = df["InvoiceDate"].min()
    log["date_max"] = df["InvoiceDate"].max()
    return df, cancellations, log
