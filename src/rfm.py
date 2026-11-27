"""Customer-level RFM table, 1-5 scores and the classic rule-based RFM segments."""
import numpy as np
import pandas as pd

# Classic RFM grid on (R score, F score). Checked top to bottom; first match wins.
RFM_RULES = [
    ("Champions",           lambda r, f: (r == 5) & (f >= 4)),
    ("Loyal",               lambda r, f: r.between(3, 4) & (f >= 4)),
    ("Potential Loyalists", lambda r, f: (r >= 4) & f.between(2, 3)),
    ("New Customers",       lambda r, f: (r == 5) & (f == 1)),
    ("Promising",           lambda r, f: (r == 4) & (f == 1)),
    ("Need Attention",      lambda r, f: (r == 3) & (f == 3)),
    ("About to Sleep",      lambda r, f: (r == 3) & (f <= 2)),
    ("Cannot Lose Them",    lambda r, f: (r <= 2) & (f == 5)),
    ("At Risk",             lambda r, f: (r <= 2) & f.between(3, 4)),
    ("Hibernating",         lambda r, f: (r <= 2) & (f <= 2)),
]


def build_customer_table(sales: pd.DataFrame, cancellations: pd.DataFrame) -> pd.DataFrame:
    """One row per customer with RFM and descriptive features."""
    snapshot = sales["InvoiceDate"].max() + pd.Timedelta(days=1)

    g = sales.groupby("CustomerID")
    cust = pd.DataFrame({
        "Recency": (snapshot - g["InvoiceDate"].max()).dt.days,
        "Frequency": g["Invoice"].nunique(),
        "Monetary": g["Revenue"].sum(),
        "TenureDays": (snapshot - g["InvoiceDate"].min()).dt.days,
        "DistinctProducts": g["StockCode"].nunique(),
        "Country": g["Country"].agg(lambda s: s.mode().iat[0]),
    })
    cust["AvgOrderValue"] = cust["Monetary"] / cust["Frequency"]

    returned = cancellations.groupby("CustomerID")["Revenue"].sum()
    cust["ReturnedValue"] = returned.reindex(cust.index).fillna(0.0)
    cust["ReturnRate"] = (cust["ReturnedValue"] / (cust["Monetary"] + cust["ReturnedValue"])).clip(0, 1)
    cust["IsUK"] = cust["Country"].eq("United Kingdom")
    cust.attrs["snapshot"] = snapshot
    return cust


def _quintile(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    # rank first so heavy ties (e.g. many 1-order customers) still split into 5 bins
    ranked = series.rank(method="first", ascending=higher_is_better)
    return pd.qcut(ranked, 5, labels=[1, 2, 3, 4, 5]).astype(int)


def score_rfm(cust: pd.DataFrame) -> pd.DataFrame:
    cust = cust.copy()
    cust["R"] = _quintile(cust["Recency"], higher_is_better=False)
    cust["F"] = _quintile(cust["Frequency"])
    cust["M"] = _quintile(cust["Monetary"])
    cust["RFM_Score"] = cust["R"] + cust["F"] + cust["M"]
    cust["RFM_Cell"] = cust["R"].astype(str) + cust["F"].astype(str) + cust["M"].astype(str)

    seg = pd.Series("Other", index=cust.index)
    unassigned = pd.Series(True, index=cust.index)
    for name, rule in RFM_RULES:
        hit = rule(cust["R"], cust["F"]) & unassigned
        seg[hit] = name
        unassigned &= ~hit
    cust["RFM_Segment"] = seg
    return cust


def pareto_stats(cust: pd.DataFrame) -> dict:
    """How concentrated is revenue? Share of revenue from the top X% of customers."""
    m = np.sort(cust["Monetary"].to_numpy())[::-1]
    cum = m.cumsum() / m.sum()
    n = len(m)
    return {f"top_{p}pct_revenue_share": float(cum[max(int(n * p / 100) - 1, 0)])
            for p in (1, 5, 10, 20, 50)}
