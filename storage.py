"""
storage.py — Persist scraped products to JSON, CSV, or HDF5.

File naming convention:
    products_<YYYYMMDD_HHMMSS>.<ext>

The timestamp is embedded in the filename so repeated scrapes are never
overwritten and historical snapshots can be compared later.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

# Optional heavy dependencies – imported lazily so the module loads even if
# the user hasn't installed every backend yet.

OUTPUT_DIR = Path("scraped_data")


def _ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


# ── JSON ──────────────────────────────────────────────────────────────────────

def _save_json(products: List[dict], timestamp: str) -> Path:
    out = _ensure_output_dir() / f"products_{timestamp}.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(products, fh, indent=2, ensure_ascii=False)
    return out


# ── CSV ───────────────────────────────────────────────────────────────────────

def _save_csv(products: List[dict], timestamp: str) -> Path:
    try:
        import pandas as pd  # type: ignore
    except ImportError:
        raise ImportError("pandas is required for CSV output.  pip install pandas")

    out = _ensure_output_dir() / f"products_{timestamp}.csv"

    # Flatten the nested 'rating' dict { rate, count } into two columns
    rows = []
    for p in products:
        row = dict(p)
        rating = row.pop("rating", {}) or {}
        row["rating_rate"]  = rating.get("rate")
        row["rating_count"] = rating.get("count")
        rows.append(row)

    df = pd.DataFrame(rows)

    # Canonical column order (extra columns appended automatically)
    priority_cols = [
        "id", "title", "price", "category", "description",
        "image", "rating_rate", "rating_count", "scraped_at",
    ]
    ordered = [c for c in priority_cols if c in df.columns]
    rest    = [c for c in df.columns if c not in priority_cols]
    df = df[ordered + rest]

    df.to_csv(out, index=False, encoding="utf-8")
    return out


# ── HDF5 ─────────────────────────────────────────────────────────────────────

def _save_hdf5(products: List[dict], timestamp: str) -> Path:
    try:
        import pandas as pd  # type: ignore
    except ImportError:
        raise ImportError("pandas is required for HDF5 output.  pip install pandas tables")
    try:
        import tables  # noqa: F401  # PyTables back-end
    except ImportError:
        raise ImportError("PyTables is required for HDF5 output.  pip install tables")

    out = _ensure_output_dir() / f"products_{timestamp}.h5"

    rows = []
    for p in products:
        row = dict(p)
        rating = row.pop("rating", {}) or {}
        row["rating_rate"]  = rating.get("rate")
        row["rating_count"] = rating.get("count")
        rows.append(row)

    df = pd.DataFrame(rows)

    # HDF5 stores cannot handle object columns with mixed types easily;
    # stringify description and image which may contain special chars.
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str)

    df.to_hdf(out, key="products", mode="w", complevel=9, complib="blosc")
    return out


# ── public API ────────────────────────────────────────────────────────────────

_WRITERS = {
    "json":  _save_json,
    "csv":   _save_csv,
    "hdf5":  _save_hdf5,
}


def save_products(products: List[dict], fmt: str, timestamp: str) -> Path:
    """
    Persist *products* in the requested *fmt* and return the output path.

    Parameters
    ----------
    products  : list of product dicts (each must include 'scraped_at')
    fmt       : 'json' | 'csv' | 'hdf5'
    timestamp : run timestamp string used in the filename
    """
    fmt = fmt.lower()
    if fmt not in _WRITERS:
        raise ValueError(f"Unsupported format '{fmt}'. Choose from: {list(_WRITERS)}")

    writer = _WRITERS[fmt]
    return writer(products, timestamp)
