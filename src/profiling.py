"""Segment profiles and the marketing playbook for each segment type."""
import pandas as pd

# Playbook keyed by the base segment name produced in clustering._base_name.
PLAYBOOK = {
    "Champions": {
        "goal": "Retain and grow share of wallet; turn into advocates.",
        "tactics": [
            "VIP tier: early access to new seasonal ranges (Christmas range launches in late summer for gift retailers).",
            "Volume-break pricing or free delivery thresholds instead of blanket discounts - these customers already buy without them.",
            "Dedicated account contact for wholesale buyers; referral incentive for other shops.",
            "Cross-sell complementary categories based on their purchase history.",
        ],
        "channel": "Personal email / account manager, catalogue preview",
        "spend": "High - protect revenue, but avoid giving margin away with discounts",
        "kpi": "Retention rate, revenue per customer, order frequency",
    },
    "Loyal Customers": {
        "goal": "Move them up to Champion-level frequency and spend.",
        "tactics": [
            "Loyalty points or tiered rewards that unlock at the next spend level.",
            "Replenishment reminders timed to their usual reorder gap.",
            "Bundle offers ('complete the display') to raise basket size.",
        ],
        "channel": "Email, personalised recommendations",
        "spend": "Medium-high",
        "kpi": "Average order value, move-up rate to Champions",
    },
    "New & Promising": {
        "goal": "Convert a first or second order into a habit.",
        "tactics": [
            "Onboarding email sequence: best-sellers, how to reorder, delivery info.",
            "Time-limited incentive on the second order (e.g. free delivery within 30 days).",
            "Ask for feedback after the first delivery to catch problems early.",
        ],
        "channel": "Automated email journey",
        "spend": "Medium - the second order is the cheapest point to build loyalty",
        "kpi": "Second-order conversion rate within 60/90 days",
    },
    "At-Risk High Value": {
        "goal": "Win back valuable customers before they are lost.",
        "tactics": [
            "Personal win-back outreach ('we miss you') with a meaningful offer.",
            "Survey or call to find out why they stopped - price, range or service.",
            "Highlight new products added since their last order.",
        ],
        "channel": "Personal email, phone for the largest accounts",
        "spend": "High per customer - recovering one is worth many new ones",
        "kpi": "Reactivation rate, revenue recovered",
    },
    "Drifting Low Spenders": {
        "goal": "Re-engage cheaply; find the ones with potential.",
        "tactics": [
            "Low-cost automated nudges: seasonal newsletters, sale announcements.",
            "Small discount trigger after a set number of inactive days.",
            "Test offers on a sample before rolling out to the whole group.",
        ],
        "channel": "Bulk email",
        "spend": "Low",
        "kpi": "Email-to-order conversion, cost per reactivation",
    },
    "Lapsed": {
        "goal": "Minimise spend; one last reactivation attempt.",
        "tactics": [
            "One final win-back campaign with the strongest offer, then suppress from regular sends.",
            "Move to low-frequency list (major seasonal sales only) to protect email deliverability.",
            "Use as a lookalike exclusion set in paid acquisition.",
        ],
        "channel": "Single email campaign, then suppression",
        "spend": "Minimal",
        "kpi": "Reactivation rate vs campaign cost",
    },
}


def base_name(segment: str) -> str:
    return segment.split(" (tier")[0]


def segment_profiles(cust: pd.DataFrame) -> pd.DataFrame:
    total_rev = cust["Monetary"].sum()
    g = cust.groupby(["Cluster", "Segment"])
    prof = pd.DataFrame({
        "Customers": g.size(),
        "RevenueTotal": g["Monetary"].sum(),
        "MedianRecencyDays": g["Recency"].median(),
        "MedianOrders": g["Frequency"].median(),
        "MedianSpend": g["Monetary"].median(),
        "MeanSpend": g["Monetary"].mean(),
        "MedianAOV": g["AvgOrderValue"].median(),
        "MedianTenureDays": g["TenureDays"].median(),
        "MedianDistinctProducts": g["DistinctProducts"].median(),
        "ReturnRate": g["ReturnedValue"].sum() / (g["Monetary"].sum() + g["ReturnedValue"].sum()),
        "UKShare": g["IsUK"].mean(),
        "MeanR": g["R"].mean(), "MeanF": g["F"].mean(), "MeanM": g["M"].mean(),
    }).reset_index()
    prof["PctCustomers"] = prof["Customers"] / prof["Customers"].sum()
    prof["PctRevenue"] = prof["RevenueTotal"] / total_rev
    prof["RevenueIndex"] = prof["PctRevenue"] / prof["PctCustomers"]   # >1 = over-indexes
    return prof.sort_values("Cluster").reset_index(drop=True)


def cluster_vs_rfm(cust: pd.DataFrame) -> pd.DataFrame:
    """Share of each k-means cluster falling in each rule-based RFM segment."""
    return pd.crosstab(cust["Segment"], cust["RFM_Segment"], normalize="index")
