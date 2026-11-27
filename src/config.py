"""Project-wide settings. Change paths and parameters here, not in the modules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
FIG_DIR = OUTPUT_DIR / "figures"

# Default input: the UCI workbook (both sheets are read). A CSV export also works.
RAW_FILE = DATA_DIR / "online_retail_II.xlsx"

# StockCodes that are not products (postage, fees, manual adjustments, tests).
NON_PRODUCT_CODES = {
    "POST", "DOT", "M", "D", "C2", "CRUK", "BANK CHARGES", "AMAZONFEE",
    "PADS", "ADJUST", "ADJUST2", "TEST001", "TEST002", "S", "B", "m",
}

# Clustering
K_RANGE = range(2, 11)        # candidate k values to evaluate
RANDOM_STATE = 42
SILHOUETTE_SAMPLE = 3000      # sample size for silhouette (full set is slow)
FORCE_K = None                # set an int to override the automatic choice

# Chart palette (validated categorical order, light mode)
PALETTE = ["#257de0", "#f47230", "#00b894", "#f2a600", "#ee7fac",
           "#008a17", "#6a4ce2", "#ec4647"]
TEXT = "#191919"
TEXT_2 = "#666666"
GRID = "#e6e6e6"
