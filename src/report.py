"""Charts (PNG) and the auto-generated markdown report."""
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config
from .profiling import PLAYBOOK, base_name

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.edgecolor": config.GRID, "axes.labelcolor": config.TEXT_2,
    "xtick.color": config.TEXT_2, "ytick.color": config.TEXT_2,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": config.TEXT,
    "axes.titlelocation": "left", "figure.dpi": 150, "savefig.bbox": "tight",
})


def _seg_colors(prof):
    return {s: config.PALETTE[i % len(config.PALETTE)] for i, s in enumerate(prof["Segment"])}


def _grid(ax, axis="y"):
    ax.grid(axis=axis, color=config.GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def fig_k_selection(scores: pd.DataFrame, k: int, path):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    for ax, col, title in [(axes[0], "inertia", "Elbow: within-cluster inertia"),
                           (axes[1], "silhouette", "Silhouette score (higher is better)")]:
        ax.plot(scores["k"], scores[col], color=config.PALETTE[0], linewidth=2,
                marker="o", markersize=6, markeredgecolor="white", markeredgewidth=1.5)
        sel = scores.loc[scores["k"] == k, col].iat[0]
        ax.scatter([k], [sel], s=110, color=config.PALETTE[1], zorder=3,
                   edgecolor="white", linewidth=2)
        ax.annotate(f"chosen k = {k}", (k, sel), xytext=(8, 8),
                    textcoords="offset points", color=config.TEXT, fontsize=9)
        ax.set_title(title); ax.set_xlabel("Number of clusters (k)")
        ax.set_xticks(scores["k"]); _grid(ax)
    fig.savefig(path); plt.close(fig)


def fig_share(prof: pd.DataFrame, path):
    """% of customers vs % of revenue per segment - the core 'who is worth most' chart."""
    fig, ax = plt.subplots(figsize=(9, 0.75 * len(prof) + 1.4))
    y = np.arange(len(prof))[::-1]
    h = 0.36
    b1 = ax.barh(y + h / 2 + 0.01, prof["PctCustomers"] * 100, h, color=config.PALETTE[0], label="% of customers")
    b2 = ax.barh(y - h / 2 - 0.01, prof["PctRevenue"] * 100, h, color=config.PALETTE[1], label="% of revenue")
    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_width() + 0.6, bar.get_y() + bar.get_height() / 2,
                    f"{bar.get_width():.0f}%", va="center", fontsize=8.5, color=config.TEXT)
    ax.set_yticks(y, prof["Segment"])
    ax.set_xlabel("Share (%)")
    ax.set_title("Share of customers vs share of revenue, by segment")
    ax.legend(frameon=False, loc="lower right")
    ax.set_xlim(0, max(prof["PctCustomers"].max(), prof["PctRevenue"].max()) * 100 * 1.15)
    _grid(ax, "x")
    fig.savefig(path); plt.close(fig)


def fig_profiles(prof: pd.DataFrame, path):
    """Small multiples: median recency, orders and spend per segment."""
    colors = _seg_colors(prof)
    metrics = [("MedianRecencyDays", "Days since last order", "{:.0f}"),
               ("MedianOrders", "Number of orders", "{:.0f}"),
               ("MedianSpend", "Total spend (£)", "£{:,.0f}")]
    fig, axes = plt.subplots(1, 3, figsize=(12, 0.6 * len(prof) + 1.6), sharey=True)
    y = np.arange(len(prof))[::-1]
    for ax, (col, title, fmt) in zip(axes, metrics):
        vals = prof[col]
        ax.barh(y, vals, 0.6, color=[colors[s] for s in prof["Segment"]])
        for yi, v in zip(y, vals):
            ax.text(v * 1.02 + vals.max() * 0.01, yi, fmt.format(v), va="center", fontsize=8.5, color=config.TEXT)
        ax.set_title(f"Median: {title.lower()}", fontsize=10.5)
        ax.set_xlim(0, vals.max() * 1.3); _grid(ax, "x")
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    axes[0].set_yticks(y, prof["Segment"])
    fig.suptitle("Segment profiles", x=0.01, ha="left", fontweight="bold", color=config.TEXT)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_pareto(cust: pd.DataFrame, path):
    m = np.sort(cust["Monetary"].to_numpy())[::-1]
    cum = m.cumsum() / m.sum() * 100
    x = np.arange(1, len(m) + 1) / len(m) * 100
    i20 = max(int(len(m) * 0.2) - 1, 0)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(x, cum, color=config.PALETTE[0], linewidth=2)
    ax.plot([0, 100], [0, 100], color=config.TEXT_2, linewidth=1, linestyle="--")
    ax.scatter([20], [cum[i20]], s=70, color=config.PALETTE[0], edgecolor="white", linewidth=2, zorder=3)
    ax.annotate(f"Top 20% of customers = {cum[i20]:.0f}% of revenue", (20, cum[i20]),
                xytext=(12, -22), textcoords="offset points", fontsize=9, color=config.TEXT)
    ax.text(62, 52, "equal share line", fontsize=8, color=config.TEXT_2, rotation=32)
    ax.set_xlabel("% of customers (ranked by spend)"); ax.set_ylabel("Cumulative % of revenue")
    ax.set_title("Revenue concentration"); ax.set_xlim(0, 100); ax.set_ylim(0, 102)
    _grid(ax, "both")
    fig.savefig(path); plt.close(fig)


def fig_crosstab(xtab: pd.DataFrame, prof: pd.DataFrame, path):
    """How the k-means clusters map onto the classic RFM rule segments (sequential blue)."""
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq", ["#f3f7fd", "#9cc4f2", "#257de0", "#0b3d7a"])
    xtab = xtab.reindex(prof["Segment"])
    xtab = xtab.loc[:, xtab.max().sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(1.0 * xtab.shape[1] + 3, 0.6 * xtab.shape[0] + 1.8))
    ax.imshow(xtab.values, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for i in range(xtab.shape[0]):
        for j in range(xtab.shape[1]):
            v = xtab.values[i, j]
            if v >= 0.05:
                ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=8,
                        color="white" if v > 0.5 else config.TEXT)
    ax.set_xticks(range(xtab.shape[1]), xtab.columns, rotation=35, ha="right")
    ax.set_yticks(range(xtab.shape[0]), xtab.index)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks(np.arange(-.5, xtab.shape[1]), minor=True)
    ax.set_yticks(np.arange(-.5, xtab.shape[0]), minor=True)
    ax.grid(which="minor", color="white", linewidth=2); ax.tick_params(which="minor", length=0)
    ax.set_title("K-means clusters vs rule-based RFM segments (row %)")
    fig.savefig(path); plt.close(fig)


def make_figures(cust, prof, scores, k, xtab):
    config.FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig_k_selection(scores, k, config.FIG_DIR / "01_k_selection.png")
    fig_pareto(cust, config.FIG_DIR / "02_revenue_concentration.png")
    fig_share(prof, config.FIG_DIR / "03_segment_share.png")
    fig_profiles(prof, config.FIG_DIR / "04_segment_profiles.png")
    fig_crosstab(xtab, prof, config.FIG_DIR / "05_cluster_vs_rfm.png")


# ---------- markdown report ----------

def _money(x):
    return f"£{x:,.0f}"


def write_report(log, cust, prof, scores, k, pareto, path):
    top = prof.iloc[0]
    best_idx = prof.loc[prof["RevenueIndex"].idxmax()]
    risk = prof[prof["Segment"].map(base_name).eq("At-Risk High Value")]

    lines = [
        "# Customer Segmentation for an Online Gift Retailer",
        "",
        f"*RFM scoring and k-means clustering on UCI Online Retail II. Generated {date.today():%d %B %Y}.*",
        "",
        "## Business question",
        "Which customers are worth the most, and how should marketing treat each group differently?",
        "",
        "## Key findings",
        f"- **Revenue is concentrated.** The top 20% of customers generate "
        f"{pareto['top_20pct_revenue_share']:.0%} of revenue; the top 1% alone generate "
        f"{pareto['top_1pct_revenue_share']:.0%}.",
        f"- **{top['Segment']}** are the most valuable group: {top['PctCustomers']:.0%} of customers "
        f"but {top['PctRevenue']:.0%} of revenue. The median customer here has placed "
        f"{top['MedianOrders']:.0f} orders, last bought {top['MedianRecencyDays']:.0f} days ago "
        f"and spent {_money(top['MedianSpend'])}.",
    ]
    if best_idx["Segment"] == top["Segment"]:
        lines[-1] += f" Their revenue share is {top['RevenueIndex']:.1f}x their customer share, the highest of any segment."
    else:
        lines.append(f"- **{best_idx['Segment']}** over-index most on revenue: "
                     f"{best_idx['RevenueIndex']:.1f}x their share of the customer base.")
    if len(risk):
        r = risk.iloc[0]
        lines.append(
            f"- **{_money(r['RevenueTotal'])} of historical revenue sits with {r['Segment']}** "
            f"({int(r['Customers']):,} customers, median {r['MedianRecencyDays']:.0f} days since last order) - "
            "the clearest win-back opportunity.")
    low = prof.iloc[-1]
    lines += [
        f"- **{low['Segment']}** are {low['PctCustomers']:.0%} of customers but only "
        f"{low['PctRevenue']:.0%} of revenue - they should get the cheapest, most automated treatment.",
        "",
        "![Share of customers vs revenue](figures/03_segment_share.png)",
        "",
        "## Data and cleaning",
        f"- {log['raw_rows']:,} raw transaction lines, "
        f"{log['date_min']:%b %Y} to {log['date_max']:%b %Y}.",
        f"- Removed {log['duplicates_removed']:,} duplicate lines, "
        f"{log['missing_customer_removed']:,} lines with no Customer ID (cannot be segmented), "
        f"{log['non_product_removed']:,} non-product lines (postage, fees, adjustments) and "
        f"{log['nonpositive_qty_or_price_removed']:,} lines with zero/negative quantity or price.",
        f"- {log['cancellation_rows']:,} cancellation lines were set aside and used to compute each customer's return rate.",
        f"- Result: {log['clean_rows']:,} lines, {log['invoices']:,} invoices, **{log['customers']:,} customers**.",
        "",
        "## Method",
        "1. **RFM table** - per customer: Recency (days since last order, measured from the day after the last "
        "transaction in the data), Frequency (number of distinct invoices) and Monetary (total net spend).",
        "2. **RFM scores** - each metric split into quintiles (1-5), and customers mapped to the classic "
        "rule-based RFM segments as a benchmark.",
        "3. **K-means** - R, F and M are log-transformed (they are heavily skewed) and standardised, then "
        f"clustered for k = {min(scores['k'])}-{max(scores['k'])}. "
        f"**k = {k}** was chosen as the best silhouette score between 3 and 6 "
        "(k = 2 is too coarse to act on; more than 6 is more programmes than a team can run).",
        "4. **Profiling and naming** - clusters are ordered by median spend and named from their average "
        "R and F/M scores.",
        "",
        "![k selection](figures/01_k_selection.png)",
        "",
        "| k | Inertia | Silhouette | Davies-Bouldin |",
        "|---|---|---|---|",
    ]
    for _, s in scores.iterrows():
        mark = " **(chosen)**" if s["k"] == k else ""
        lines.append(f"| {int(s['k'])}{mark} | {s['inertia']:,.0f} | {s['silhouette']:.3f} | {s['davies_bouldin']:.3f} |")

    lines += [
        "",
        "## Segment overview",
        "",
        "| Segment | Customers | % customers | % revenue | Median days since order | Median orders | Median spend | Median order value | Return rate |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for _, p in prof.iterrows():
        lines.append(
            f"| {p['Segment']} | {int(p['Customers']):,} | {p['PctCustomers']:.1%} | {p['PctRevenue']:.1%} | "
            f"{p['MedianRecencyDays']:.0f} | {p['MedianOrders']:.0f} | {_money(p['MedianSpend'])} | "
            f"{_money(p['MedianAOV'])} | {p['ReturnRate']:.1%} |")
    lines += [
        "",
        "![Segment profiles](figures/04_segment_profiles.png)",
        "",
        "![Revenue concentration](figures/02_revenue_concentration.png)",
        "",
        "## Segment profiles and targeting plan",
    ]
    for _, p in prof.iterrows():
        play = PLAYBOOK[base_name(p["Segment"])]
        lines += [
            "",
            f"### {int(p['Cluster'])}. {p['Segment']}",
            f"**Size:** {int(p['Customers']):,} customers ({p['PctCustomers']:.0%}) - "
            f"**Revenue:** {_money(p['RevenueTotal'])} ({p['PctRevenue']:.0%}), "
            f"{p['RevenueIndex']:.1f}x their share of customers.",
            "",
            f"**Profile:** median {p['MedianOrders']:.0f} orders, last order {p['MedianRecencyDays']:.0f} days ago, "
            f"{_money(p['MedianSpend'])} total spend, {_money(p['MedianAOV'])} per order, "
            f"customer for {p['MedianTenureDays']:.0f} days, {p['MedianDistinctProducts']:.0f} distinct products; "
            f"{p['UKShare']:.0%} UK-based; {p['ReturnRate']:.1%} of value returned.",
            "",
            f"**Objective:** {play['goal']}",
            "",
            "**Actions:**",
        ]
        lines += [f"- {t}" for t in play["tactics"]]
        lines += [
            "",
            f"**Channel:** {play['channel']}  ",
            f"**Budget priority:** {play['spend']}  ",
            f"**Measure success by:** {play['kpi']}",
        ]
    lines += [
        "",
        "## Validation against rule-based RFM",
        "Each row shows where a k-means cluster's customers fall in the classic RFM grid. Clusters that map "
        "cleanly onto one or two RFM segments are behaving as expected; spread-out rows show where k-means "
        "draws different boundaries from fixed quintile rules.",
        "",
        "![Cluster vs RFM](figures/05_cluster_vs_rfm.png)",
        "",
        "## Limitations and next steps",
        "- Customers without an ID (a large share of lines) are excluded, so this covers known/registered customers only.",
        "- Many customers are wholesalers, so spend is skewed by a few very large accounts; a separate B2B/B2C split could sharpen the plan.",
        "- RFM is backward-looking. A next step is a predictive model (e.g. BG/NBD + Gamma-Gamma for customer lifetime value, or a churn classifier) to rank customers on future value.",
        "- Targeting actions should be tested with control groups before full rollout so uplift can be measured.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
