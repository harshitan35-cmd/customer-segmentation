"""Generate a fake transactions file with the exact Online Retail II schema.

Used only to test the pipeline without the real download:
    python tests/make_synthetic_data.py && python run_pipeline.py --input data/synthetic_online_retail.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
START, END = pd.Timestamp("2009-12-01"), pd.Timestamp("2011-12-09")
SPAN = (END - START).days

# (share of customers, mean orders, mean lines/order, qty scale, active-window shape)
ARCHETYPES = {
    "vip":      (0.07, 40, 30, 24, "all"),
    "loyal":    (0.18, 12, 20, 10, "all"),
    "new":      (0.15, 2, 15, 8, "late"),
    "churned_hi": (0.12, 10, 22, 12, "early"),
    "occasional": (0.23, 3, 12, 6, "mid"),
    "lost":     (0.25, 1.3, 10, 5, "early"),
}
products = pd.DataFrame({
    "StockCode": [f"{20000 + i}" for i in range(600)],
    "Description": [f"GIFT ITEM {i}" for i in range(600)],
    "Price": np.round(rng.lognormal(0.9, 0.7, 600), 2),
})
countries = ["United Kingdom"] * 9 + ["Germany", "France", "EIRE", "Netherlands", "Spain"]


def window(shape):
    a, b = {"all": (0, 1), "late": (0.8, 1), "early": (0, 0.45), "mid": (0.3, 0.8)}[shape]
    return START + pd.Timedelta(days=SPAN * a), START + pd.Timedelta(days=SPAN * b)


rows, inv = [], 489000
n_customers = 4000
for cid in range(12346, 12346 + n_customers):
    name = rng.choice(list(ARCHETYPES), p=[v[0] for v in ARCHETYPES.values()])
    _, mean_orders, mean_lines, qscale, shape = ARCHETYPES[name]
    lo, hi = window(shape)
    n_orders = max(1, rng.poisson(mean_orders))
    country = rng.choice(countries)
    dates = sorted(lo + pd.to_timedelta(rng.uniform(0, (hi - lo).total_seconds(), n_orders), "s"))
    for d in dates:
        inv += 1
        cancel = rng.random() < 0.03
        lines = products.sample(max(1, rng.poisson(mean_lines)), random_state=int(rng.integers(1e9)))
        qty = np.maximum(1, rng.poisson(qscale, len(lines)))
        if cancel:
            qty = -qty
        for (_, p), q in zip(lines.iterrows(), qty):
            rows.append((("C" if cancel else "") + str(inv), p.StockCode, p.Description, int(q),
                         d.floor("min"), p.Price, float(cid), country))
        if rng.random() < 0.3:  # postage line
            rows.append((str(inv), "POST", "POSTAGE", 1, d.floor("min"), 18.0, float(cid), country))

# guest checkouts with no Customer ID
for _ in range(3000):
    d = START + pd.Timedelta(days=float(rng.uniform(0, SPAN)))
    p = products.sample(1, random_state=int(rng.integers(1e9))).iloc[0]
    rows.append((str(inv), p.StockCode, p.Description, 1, d.floor("min"), p.Price, np.nan, "United Kingdom"))
    inv += 1

df = pd.DataFrame(rows, columns=["Invoice", "StockCode", "Description", "Quantity",
                                 "InvoiceDate", "Price", "Customer ID", "Country"])
df = pd.concat([df, df.sample(500, random_state=1)])  # some duplicates
out = Path(__file__).resolve().parents[1] / "data" / "synthetic_online_retail.csv"
out.parent.mkdir(exist_ok=True)
df.to_csv(out, index=False)
print(f"wrote {len(df):,} rows to {out}")
