#!/usr/bin/env python3
"""
price_history.py — Plot price history for one or more products across scrape snapshots.

Usage:
  python price_history.py --ids 1 3 5 --type csv
  python price_history.py --ids 2 --type json
  python price_history.py --ids 4 --type hdf5
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

SCRAPED_DIR = Path("scraped_data")
FILENAME_RE = re.compile(r"^products_(\d{8}_\d{6})\.")


def parse_timestamp(filename: str) -> datetime | None:
    m = FILENAME_RE.match(filename)
    if not m:
        return None
    return datetime.strptime(m.group(1), "%Y%m%d_%H%M%S")


def load_csv(path: Path) -> list[dict]:
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for CSV files.  pip install pandas")
    df = pd.read_csv(path)
    return df.to_dict(orient="records")


def load_json(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_hdf5(path: Path) -> list[dict]:
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for HDF5 files.  pip install pandas tables")
    df = pd.read_hdf(path, key="products")
    return df.to_dict(orient="records")


LOADERS = {
    "csv":  load_csv,
    "json": load_json,
    "hdf5": load_hdf5,
}

EXT_MAP = {
    "csv":  "csv",
    "json": "json",
    "hdf5": "h5",
}


def collect_history(product_ids: list[int], file_type: str) -> dict[int, dict]:
    """
    Returns {product_id: {"title": str, "points": [(datetime, float), ...]}}
    """
    ext = EXT_MAP[file_type]
    loader = LOADERS[file_type]

    files = sorted(
        (f for f in SCRAPED_DIR.iterdir() if f.suffix.lstrip(".") == ext and FILENAME_RE.match(f.name)),
        key=lambda f: f.name,
    )

    if not files:
        print(f"No {file_type} files found in {SCRAPED_DIR}/")
        sys.exit(1)

    history = {pid: {"title": None, "points": []} for pid in product_ids}

    for fpath in files:
        ts = parse_timestamp(fpath.name)
        if ts is None:
            continue
        try:
            records = loader(fpath)
        except Exception as e:
            print(f"  Warning: could not read {fpath.name}: {e}")
            continue

        by_id = {int(r["id"]): r for r in records if "id" in r}

        for pid in product_ids:
            row = by_id.get(pid)
            if row is None:
                continue
            try:
                price = float(row["price"])
            except (KeyError, TypeError, ValueError):
                continue

            history[pid]["points"].append((ts, price))
            if history[pid]["title"] is None:
                history[pid]["title"] = str(row.get("title", f"Product {pid}"))

    return history


def plot_history(history: dict[int, dict]):
    fig, ax = plt.subplots(figsize=(10, 5))

    any_data = False
    for pid, data in history.items():
        points = data["points"]
        if not points:
            print(f"  No data found for product id={pid}")
            continue
        any_data = True

        times, prices = zip(*points)
        label = f"[{pid}] {data['title']}" if data["title"] else f"Product {pid}"

        line, = ax.plot(times, prices, marker="o", linewidth=1.8, label=label)

        # Annotate each point with its price
        for t, p in zip(times, prices):
            ax.annotate(
                f"${p:.2f}",
                xy=(t, p),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color=line.get_color(),
            )

    if not any_data:
        print("No data to plot.")
        sys.exit(1)

    # X-axis formatting
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d\n%H:%M"))
    fig.autofmt_xdate(rotation=0, ha="center")

    ax.set_xlabel("Scrape date/time", labelpad=8)
    ax.set_ylabel("Price (USD)")

    if len(history) == 1:
        pid = next(iter(history))
        title = history[pid]["title"] or f"Product {pid}"
        ax.set_title(f"Price history — {title}")
    else:
        ax.set_title("Price history — selected products")

    ax.legend(loc="best", fontsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.show()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="price_history.py",
        description="Plot price history for products across scrape snapshots.",
    )
    parser.add_argument(
        "--ids",
        metavar="ID",
        nargs="+",
        type=int,
        required=True,
        help="One or more product IDs to plot (e.g. --ids 1 3 5)",
    )
    parser.add_argument(
        "--type",
        dest="file_type",
        choices=["csv", "json", "hdf5"],
        required=True,
        help="File type to read from scraped_data/",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    print(f"Reading {args.file_type} snapshots for product(s): {args.ids}")
    history = collect_history(args.ids, args.file_type)
    plot_history(history)


if __name__ == "__main__":
    main()
