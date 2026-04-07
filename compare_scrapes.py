"""
compare_scrapes.py — Compare product data across scraped CSV snapshots.

Loads all CSV files in scraped_data/, sorts them by timestamp, and reports:
  - Price changes per product
  - Rating changes per product
  - Products added or removed between snapshots
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SCRAPED_DIR = Path("scraped_data")
NUMERIC_COLS = ["price", "rating_rate", "rating_count"]


def load_snapshots() -> list[tuple[str, pd.DataFrame]]:
    """Return list of (timestamp, DataFrame) sorted chronologically."""
    files = sorted(SCRAPED_DIR.glob("products_*.csv"))
    if not files:
        print(f"No CSV files found in {SCRAPED_DIR}/")
        return []

    snapshots = []
    for f in files:
        # Extract timestamp from filename: products_YYYYMMDD_HHMMSS.csv
        ts = f.stem.replace("products_", "")
        df = pd.read_csv(f)
        snapshots.append((ts, df))
        print(f"  Loaded {f.name}  ({len(df)} products)")
    return snapshots


def compare_pair(ts_a: str, df_a: pd.DataFrame, ts_b: str, df_b: pd.DataFrame) -> None:
    """Print differences between two consecutive snapshots."""
    print(f"\n{'='*60}")
    print(f"Comparing  {ts_a}  ->  {ts_b}")
    print(f"{'='*60}")

    ids_a = set(df_a["id"])
    ids_b = set(df_b["id"])

    added   = ids_b - ids_a
    removed = ids_a - ids_b

    if added:
        print(f"\n  [+] Products added ({len(added)}): {sorted(added)}")
    if removed:
        print(f"\n  [-] Products removed ({len(removed)}): {sorted(removed)}")

    # Compare common products
    common_ids = ids_a & ids_b
    a_indexed = df_a[df_a["id"].isin(common_ids)].set_index("id")
    b_indexed = df_b[df_b["id"].isin(common_ids)].set_index("id")

    changes_found = False
    for col in NUMERIC_COLS:
        if col not in a_indexed.columns or col not in b_indexed.columns:
            continue

        diff = b_indexed[col] - a_indexed[col]
        changed = diff[diff != 0].dropna()

        if changed.empty:
            continue

        changes_found = True
        print(f"\n  [{col}] changed in {len(changed)} product(s):")
        for prod_id, delta in changed.items():
            old_val = a_indexed.loc[prod_id, col]
            new_val = b_indexed.loc[prod_id, col]
            title   = b_indexed.loc[prod_id, "title"] if "title" in b_indexed.columns else ""
            sign    = "+" if delta > 0 else ""
            print(f"    id={prod_id:3}  {old_val} → {new_val}  ({sign}{delta:.4g})  {title[:50]}")

    if not changes_found and not added and not removed:
        print("\n  No differences found — snapshots are identical.")


def main() -> None:
    print(f"Scanning {SCRAPED_DIR}/ for CSV snapshots...\n")
    snapshots = load_snapshots()

    if len(snapshots) < 2:
        print("\nNeed at least 2 snapshots to compare.")
        return

    for (ts_a, df_a), (ts_b, df_b) in zip(snapshots, snapshots[1:]):
        compare_pair(ts_a, df_a, ts_b, df_b)

    print("\nDone.")


if __name__ == "__main__":
    main()
