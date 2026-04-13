#!/usr/bin/env python3
"""
compare_scrapes.py — Compare product snapshots across scrape runs.

Usage
-----
    python compare_scrapes.py json
    python compare_scrapes.py csv
    python compare_scrapes.py hdf5

The script scans the `scraped_data/` folder for all files matching the chosen
format, loads them chronologically, and for every consecutive pair of snapshots
reports:

  • Products whose price changed
  • Products whose description changed
  • Products whose rating changed (rate or count)
  • Products that appeared   (new in the later snapshot)
  • Products that disappeared (present in the earlier snapshot, gone in the later one)

A final cross-run price timeline is printed for every product seen across all
snapshots, making it easy to spot trends at a glance.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# ── constants ─────────────────────────────────────────────────────────────────

SCRAPED_DATA_DIR = Path("scraped_data")

# Fields we actively compare between snapshots (title excluded intentionally:
# a title change would almost certainly mean a different product)
TRACKED_FIELDS: list[str] = ["price", "description", "rating_rate", "rating_count"]

# ANSI colour helpers (gracefully disabled on Windows without colour support)
try:
    import os
    _COLOURS = os.get_terminal_size() and sys.stdout.isatty()
except Exception:
    _COLOURS = False

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOURS else text

RED    = lambda t: _c(t, "31")
GREEN  = lambda t: _c(t, "32")
YELLOW = lambda t: _c(t, "33")
CYAN   = lambda t: _c(t, "36")
BOLD   = lambda t: _c(t, "1")
DIM    = lambda t: _c(t, "2")


# ── loaders ───────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    # Normalise: flatten nested rating dict if present
    rows = []
    for item in data:
        row = dict(item)
        if "rating" in row and isinstance(row["rating"], dict):
            row["rating_rate"]  = row["rating"].get("rate")
            row["rating_count"] = row["rating"].get("count")
            del row["rating"]
        rows.append(row)
    return rows


def _load_csv(path: Path) -> list[dict]:
    try:
        import pandas as pd
    except ImportError:
        sys.exit("pandas is required for CSV mode.  pip install pandas")

    df = pd.read_csv(path, dtype={"id": int})
    # Coerce numeric columns that pandas may read as str
    for col in ("price", "rating_rate"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ("rating_count",):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df.to_dict(orient="records")


def _load_hdf5(path: Path) -> list[dict]:
    try:
        import pandas as pd
    except ImportError:
        sys.exit("pandas is required for HDF5 mode.  pip install pandas tables")
    try:
        import tables  # noqa: F401
    except ImportError:
        sys.exit("PyTables is required for HDF5 mode.  pip install tables")

    df = pd.read_hdf(path, key="products")
    return df.to_dict(orient="records")


_LOADERS = {
    "json": (_load_json, "*.json"),
    "csv":  (_load_csv,  "*.csv"),
    "hdf5": (_load_hdf5, "*.h5"),
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _snapshot_ts(path: Path) -> str:
    """Extract timestamp string from filename, fallback to stem."""
    stem = path.stem                          # e.g. products_20240401_080000
    parts = stem.split("_", 1)
    return parts[1] if len(parts) == 2 else stem


def _fmt_val(val: Any) -> str:
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val) if val is not None else "—"


def _changed(old: Any, new: Any) -> bool:
    """Return True if values differ meaningfully (tolerates float precision)."""
    if old is None and new is None:
        return False
    if old is None or new is None:
        return True
    if isinstance(old, float) or isinstance(new, float):
        try:
            return abs(float(old) - float(new)) > 1e-9
        except (TypeError, ValueError):
            pass
    return str(old) != str(new)


def _section(title: str) -> None:
    width = 70
    print()
    print(BOLD("═" * width))
    print(BOLD(f"  {title}"))
    print(BOLD("═" * width))


def _sub(title: str) -> None:
    print()
    print(CYAN(f"  ── {title}"))


# ── core diff engine ──────────────────────────────────────────────────────────

def _diff_snapshots(
    snap_a: list[dict],
    snap_b: list[dict],
    ts_a: str,
    ts_b: str,
) -> None:
    """Print a human-readable diff between two consecutive snapshots."""

    ids_a = {int(p["id"]): p for p in snap_a}
    ids_b = {int(p["id"]): p for p in snap_b}

    added   = sorted(set(ids_b) - set(ids_a))
    removed = sorted(set(ids_a) - set(ids_b))
    common  = sorted(set(ids_a) & set(ids_b))

    _section(f"Snapshot  {DIM(ts_a)}  →  {DIM(ts_b)}")

    # ── new products ──────────────────────────────────────────────────────────
    if added:
        _sub(f"New products  (+{len(added)})")
        for pid in added:
            p = ids_b[pid]
            print(GREEN(f"    + [{pid:>3}]  {p.get('title','?')[:55]:<55}  ${_fmt_val(p.get('price'))}"))
    else:
        _sub("New products")
        print(DIM("    (none)"))

    # ── removed products ──────────────────────────────────────────────────────
    if removed:
        _sub(f"Removed products  (-{len(removed)})")
        for pid in removed:
            p = ids_a[pid]
            print(RED(f"    - [{pid:>3}]  {p.get('title','?')[:55]:<55}  ${_fmt_val(p.get('price'))}"))
    else:
        _sub("Removed products")
        print(DIM("    (none)"))

    # ── changed fields ────────────────────────────────────────────────────────
    changes_found = False
    field_changes: dict[str, list[str]] = {f: [] for f in TRACKED_FIELDS}

    for pid in common:
        pa, pb = ids_a[pid], ids_b[pid]
        for field in TRACKED_FIELDS:
            va, vb = pa.get(field), pb.get(field)
            if _changed(va, vb):
                label = f"[{pid:>3}] {pa.get('title','?')[:40]:<40}"
                if field == "price":
                    try:
                        pct = (float(vb) - float(va)) / float(va) * 100
                        arrow = GREEN("▲") if pct > 0 else RED("▼")
                        line = (f"    {arrow} {label}  "
                                f"{_fmt_val(va)} → {BOLD(_fmt_val(vb))}  "
                                f"({'+' if pct>0 else ''}{pct:.1f}%)")
                    except (TypeError, ValueError):
                        line = f"      {label}  {_fmt_val(va)} → {BOLD(_fmt_val(vb))}"
                else:
                    line = f"      {label}  {DIM(_fmt_val(va))} → {BOLD(_fmt_val(vb))}"
                field_changes[field].append(line)
                changes_found = True

    for field in TRACKED_FIELDS:
        lines = field_changes[field]
        label = field.replace("_", " ").title()
        _sub(f"{label} changes  ({len(lines)})")
        if lines:
            for line in lines:
                print(line)
        else:
            print(DIM("    (none)"))

    if not changes_found and not added and not removed:
        print()
        print(DIM("  ✔  Snapshots are identical — no changes detected."))


# ── price timeline ────────────────────────────────────────────────────────────

def _price_timeline(snapshots: list[tuple[str, list[dict]]]) -> None:
    """Show a price history table for every product across all snapshots."""
    if len(snapshots) < 2:
        return

    timestamps = [ts for ts, _ in snapshots]

    # Build {id: {ts: price, title: ...}}
    product_history: dict[int, dict] = {}
    for ts, products in snapshots:
        for p in products:
            pid = int(p["id"])
            if pid not in product_history:
                product_history[pid] = {"title": p.get("title", "?")}
            product_history[pid][ts] = p.get("price")

    _section("Price timeline — all products across all snapshots")
    print()

    col_w = 14
    header = f"  {'ID':>4}  {'Title':<40}  " + "  ".join(f"{t:>{col_w}}" for t in timestamps)
    print(BOLD(header))
    print(DIM("  " + "─" * (len(header) - 2)))

    for pid in sorted(product_history):
        info   = product_history[pid]
        title  = info["title"][:38]
        prices = [info.get(ts) for ts in timestamps]

        # Highlight products that have at least one price change
        has_change = any(
            prices[i] is not None and prices[i+1] is not None and
            abs(float(prices[i]) - float(prices[i+1])) > 1e-9
            for i in range(len(prices)-1)
        )

        price_cells = []
        for i, price in enumerate(prices):
            cell = f"${_fmt_val(price):>{col_w-1}}" if price is not None else f"{'—':>{col_w}}"
            if has_change and i > 0 and prices[i] is not None and prices[i-1] is not None:
                try:
                    diff = float(prices[i]) - float(prices[i-1])
                    cell = GREEN(cell) if diff > 0 else (RED(cell) if diff < 0 else cell)
                except (TypeError, ValueError):
                    pass
            price_cells.append(f"{cell:>{col_w}}")

        row = f"  {pid:>4}  {title:<40}  " + "  ".join(price_cells)
        print(YELLOW(row) if has_change else row)

    print()
    print(DIM("  Green = price increase   Red = price decrease   Yellow row = at least one change"))


# ── summary stats ─────────────────────────────────────────────────────────────

def _summary(snapshots: list[tuple[str, list[dict]]]) -> None:
    _section("Summary")
    print()
    print(f"  {'Snapshot':<25}  {'Products':>8}  {'Avg price':>10}  {'Min price':>10}  {'Max price':>10}")
    print(DIM("  " + "─" * 70))
    for ts, products in snapshots:
        prices = [float(p["price"]) for p in products if p.get("price") is not None]
        avg = sum(prices) / len(prices) if prices else 0
        mn  = min(prices) if prices else 0
        mx  = max(prices) if prices else 0
        print(f"  {ts:<25}  {len(products):>8}  {avg:>10.2f}  {mn:>10.2f}  {mx:>10.2f}")
    print()


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1].lower() not in _LOADERS:
        print(__doc__)
        print("Error: provide exactly one format argument — json | csv | hdf5")
        sys.exit(1)

    fmt = sys.argv[1].lower()
    loader, glob_pat = _LOADERS[fmt]

    if not SCRAPED_DATA_DIR.exists():
        sys.exit(f"Directory '{SCRAPED_DATA_DIR}' not found. Run the scraper first.")

    files = sorted(SCRAPED_DATA_DIR.glob(glob_pat))
    if not files:
        sys.exit(f"No {fmt.upper()} files found in '{SCRAPED_DATA_DIR}'.")

    print(BOLD(f"\n  compare_scrapes.py  —  format: {fmt.upper()}"))
    print(DIM(f"  Scanning '{SCRAPED_DATA_DIR}' …\n"))

    snapshots: list[tuple[str, list[dict]]] = []
    for f in files:
        ts = _snapshot_ts(f)
        try:
            products = loader(f)
            snapshots.append((ts, products))
            print(f"  {GREEN('✔')}  {f.name:<45}  {len(products):>3} products  [ts: {ts}]")
        except Exception as exc:
            print(f"  {RED('✗')}  {f.name}  →  {exc}", file=sys.stderr)

    if len(snapshots) < 2:
        print("\n  Only one snapshot found — nothing to compare.")
        _summary(snapshots)
        return

    _summary(snapshots)

    # Pairwise diffs
    for i in range(len(snapshots) - 1):
        ts_a, snap_a = snapshots[i]
        ts_b, snap_b = snapshots[i + 1]
        _diff_snapshots(snap_a, snap_b, ts_a, ts_b)

    _price_timeline(snapshots)


if __name__ == "__main__":
    main()