# FakeStore API — Data Quality & Wrangling

A Python toolkit for scraping, storing, and comparing product data from [FakeStoreAPI](https://fakestoreapi.com).

## Project structure

```
api_fakestore/
├── api_client.py       # HTTP client for FakeStoreAPI
├── storage.py          # Save scraped data to CSV / JSON / HDF5
├── store_scrapper.py   # CLI: scrape and manage products
├── compare_scrapes.py  # Compare snapshots to detect changes
├── price_history.py    # Plot price over time for one or more products
└── scraped_data/       # Output directory for scrape snapshots
```

## Requirements

```bash
pip install requests pandas matplotlib
```

> HDF5 support also requires `tables`: `pip install tables`

---

## store_scrapper.py

Scrape products and interact with the API.

```bash
# Scrape all products and save as CSV
python store_scrapper.py -s csv

# Other formats
python store_scrapper.py -s json
python store_scrapper.py -s hdf5

# Get a single product
python store_scrapper.py --get 1

# List all categories
python store_scrapper.py --categories

# List products by category
python store_scrapper.py --by-category "men's clothing"

# Add / update / delete (fake — not persisted server-side)
python store_scrapper.py --add
python store_scrapper.py --update 1
python store_scrapper.py --delete 1
```

Each scrape writes a timestamped file to `scraped_data/`, e.g. `products_20260407_133412.csv`.

---

## compare_scrapes.py

Detects differences across multiple CSV snapshots — useful for tracking price changes, rating shifts, or products appearing/disappearing between scrape runs.

### Usage

```bash
python compare_scrapes.py
```

No arguments needed. The script automatically reads all `products_*.csv` files from `scraped_data/` and compares them in chronological order.

### What it reports

| Check | Description |
|---|---|
| Price changes | Products whose `price` changed between snapshots |
| Rating changes | Products whose `rating_rate` or `rating_count` changed |
| Products added | IDs present in the newer snapshot but not the older one |
| Products removed | IDs present in the older snapshot but missing in the newer one |

### Example output

```
Scanning scraped_data/ for CSV snapshots...

  Loaded products_20260407_133412.csv  (20 products)
  Loaded products_20260407_143415.csv  (20 products)

============================================================
Comparing  20260407_133412  ->  20260407_143415
============================================================

  [price] changed in 2 product(s):
    id=  3  55.99 -> 49.99  (-6)    Mens Cotton Jacket
    id= 12  13.99 -> 15.49  (+1.5)  WD 2TB Elements Portable...

  [rating_count] changed in 1 product(s):
    id=  3  500 -> 512  (+12)  Mens Cotton Jacket
```

If no differences are found between two snapshots:

```
  No differences found -- snapshots are identical.
```

### Workflow

1. Run `store_scrapper.py -s csv` multiple times (at different times or days).
2. Run `compare_scrapes.py` to see what changed between runs.

---

## price_history.py

Plots the price of one or more products over time, using all available scrape snapshots of a given file type. The scrape timestamp is extracted from each filename (`products_YYYYMMDD_HHMMSS.<ext>`) and used as the X-axis.

### Usage

```bash
# Single product — reads all CSV snapshots
python price_history.py --ids 1 --type csv

# Multiple products on one chart
python price_history.py --ids 1 3 5 --type csv

# Using JSON or HDF5 snapshots
python price_history.py --ids 2 --type json
python price_history.py --ids 4 --type hdf5
```

| Argument | Required | Description |
|---|---|---|
| `--ids` | Yes | One or more product IDs to plot |
| `--type` | Yes | Snapshot file type: `csv`, `json`, or `hdf5` |

### What it shows

- A line chart with one series per product
- Each data point marked with its price (`$xx.xx`)
- X-axis labeled with the scrape date and time
- Chart title includes the product name (single product) or "selected products" (multi)

### Workflow

1. Run `store_scrapper.py -s csv` multiple times to accumulate snapshots.
2. Run `price_history.py --ids <id> --type csv` to visualise price trends.
