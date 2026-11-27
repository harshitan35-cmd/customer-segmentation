"""Run the full segmentation pipeline.

    python run_pipeline.py                         # uses data/online_retail_II.xlsx
    python run_pipeline.py --input data/my.csv     # or a CSV export
    python run_pipeline.py --k 5                   # force a number of clusters
"""
import argparse
import json
from pathlib import Path

from src import config
from src.clustering import choose_k, evaluate_k, fit_kmeans, label_clusters, prepare_features
from src.data_prep import clean, load_raw
from src.profiling import cluster_vs_rfm, segment_profiles
from src.report import make_figures, write_report
from src.rfm import build_customer_table, pareto_stats, score_rfm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=config.RAW_FILE)
    ap.add_argument("--k", type=int, default=None)
    args = ap.parse_args()
    if args.k:
        config.FORCE_K = args.k

    print(f"Loading {args.input} ...")
    raw = load_raw(args.input)
    sales, cancels, log = clean(raw)
    print(f"  {log['clean_rows']:,} clean lines, {log['customers']:,} customers")

    cust = score_rfm(build_customer_table(sales, cancels))

    X, _ = prepare_features(cust)
    print("Evaluating k ...")
    scores = evaluate_k(X)
    k = choose_k(scores)
    print(scores.round(3).to_string(index=False))
    print(f"  -> k = {k}")

    km = fit_kmeans(X, k)
    cust = label_clusters(cust, km.labels_)
    prof = segment_profiles(cust)
    xtab = cluster_vs_rfm(cust)
    pareto = pareto_stats(cust)

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cust.to_csv(config.OUTPUT_DIR / "customer_segments.csv")
    prof.to_csv(config.OUTPUT_DIR / "segment_profiles.csv", index=False)
    scores.to_csv(config.OUTPUT_DIR / "k_selection.csv", index=False)
    (config.OUTPUT_DIR / "pareto.json").write_text(json.dumps(pareto, indent=2))

    make_figures(cust, prof, scores, k, xtab)
    write_report(log, cust, prof, scores, k, pareto, config.OUTPUT_DIR / "segmentation_report.md")

    cols = ["Segment", "Customers", "PctCustomers", "PctRevenue", "MedianRecencyDays", "MedianOrders", "MedianSpend"]
    print("\n" + prof[cols].round(3).to_string(index=False))
    print(f"\nDone. Report: {config.OUTPUT_DIR / 'segmentation_report.md'}")


if __name__ == "__main__":
    main()
