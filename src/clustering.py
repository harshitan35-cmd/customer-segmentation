"""K-means on log-transformed, standardised RFM, with k selection and cluster naming."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from . import config

FEATURES = ["Recency", "Frequency", "Monetary"]


def prepare_features(cust: pd.DataFrame) -> tuple[np.ndarray, StandardScaler]:
    """RFM is heavily right-skewed; log1p then z-score so no single metric dominates."""
    X = np.log1p(cust[FEATURES].clip(lower=0))
    scaler = StandardScaler().fit(X)
    return scaler.transform(X), scaler


def evaluate_k(X: np.ndarray, k_range=config.K_RANGE) -> pd.DataFrame:
    rng = np.random.default_rng(config.RANDOM_STATE)
    idx = rng.choice(len(X), size=min(config.SILHOUETTE_SAMPLE, len(X)), replace=False)
    rows = []
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=config.RANDOM_STATE).fit(X)
        rows.append({
            "k": k,
            "inertia": km.inertia_,
            "silhouette": silhouette_score(X[idx], km.labels_[idx]),
            "davies_bouldin": davies_bouldin_score(X, km.labels_),
        })
    return pd.DataFrame(rows)


def choose_k(scores: pd.DataFrame) -> int:
    """Best silhouette among k = 3..6.

    k = 2 usually wins on silhouette for RFM data but only splits 'good' from
    'bad' customers, which is too coarse to act on. More than 6 segments is
    more than a marketing team can run distinct programmes for.
    """
    if config.FORCE_K:
        return int(config.FORCE_K)
    usable = scores[scores["k"].between(3, 6)]
    return int(usable.loc[usable["silhouette"].idxmax(), "k"])


def fit_kmeans(X: np.ndarray, k: int) -> KMeans:
    return KMeans(n_clusters=k, n_init=20, random_state=config.RANDOM_STATE).fit(X)


def _base_name(r: float, fm: float) -> str:
    """Name a cluster from its mean R score and mean (F+M)/2 score, both on 1-5."""
    if r >= 4 and fm >= 4:
        return "Champions"
    if r >= 3.3 and fm >= 3:
        return "Loyal Customers"
    if r >= 3.3:
        return "New & Promising"
    if fm >= 3:
        return "At-Risk High Value"
    if r >= 2.2:
        return "Drifting Low Spenders"
    return "Lapsed"


def label_clusters(cust: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
    """Attach cluster ids ordered by value (1 = most valuable) and business names."""
    cust = cust.copy()
    cust["_raw"] = labels
    order = (cust.groupby("_raw")["Monetary"].median()
             .sort_values(ascending=False).index.tolist())
    remap = {raw: i + 1 for i, raw in enumerate(order)}
    cust["Cluster"] = cust["_raw"].map(remap)

    means = cust.groupby("Cluster")[["R", "F", "M"]].mean()
    names, seen = {}, {}
    for cid, row in means.iterrows():          # already in value order
        base = _base_name(row["R"], (row["F"] + row["M"]) / 2)
        if base == "Champions" and "Champions" in seen:
            base = "Loyal Customers"      # only the top cluster can be Champions
        seen[base] = seen.get(base, 0) + 1
        names[cid] = base if seen[base] == 1 else f"{base} (tier {seen[base]})"
    cust["Segment"] = cust["Cluster"].map(names)
    return cust.drop(columns="_raw")
