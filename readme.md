# International University (Internationale Hochschule) - Written assignment complementary project

```
This academic project is complementary to written assignment of the course "Data Quality and Data Wrangling" (DLBDSDQDW01)

Task: Scrape the Web
Student Name: Juan Carlos Laverde
Student Id: UPS10797707
Tutor: Dr. PhD. Christian Müller-Kett


The project has as purpose to practice and train the skills acquired along the course
specifically scrapping a web application through APIs, in this case

```

# store_scrapper — FakeStoreAPI Python Client

A command-line tool to **scrape, store, and manage** products from
[FakeStoreAPI](https://fakestoreapi.com).

---

## Project layout

```
store_scrapper/
├── store_scrapper.py   # CLI entry-point
├── api_client.py       # HTTP client (GET / POST / PUT / PATCH / DELETE)
├── storage.py          # Writers: JSON · CSV · HDF5
├── requirements.txt
└── scraped_data/       # Created automatically on first scrape
    └── products_<TIMESTAMP>.<ext>
```

---

## Installation

```bash
pip install -r requirements.txt
```

> **HDF5 only** – `tables` (PyTables) is only required when you use
> `--store hdf5`. The rest of the tool works with just `requests` + `pandas`.

---

## Usage

### Scrape & store all products

```bash
# Save as JSON
python store_scrapper.py -s json

# Save as CSV
python store_scrapper.py -s csv

# Save as HDF5
python store_scrapper.py -s hdf5
```

Output files are written to `scraped_data/` with the run timestamp embedded in
the filename, e.g.:

```
scraped_data/products_20240407_153012.json
scraped_data/products_20240407_153012.csv
scraped_data/products_20240407_153012.h5
```

Every record includes a `scraped_at` field (`YYYYMMDD_HHMMSS`) so you can
track price / description changes across multiple runs.

---

### Other commands

| Command                                              | Description                       |
| ---------------------------------------------------- | --------------------------------- |
| `python store_scrapper.py --get 3`                   | Fetch and display product ID 3    |
| `python store_scrapper.py --add`                     | Interactively add a new product   |
| `python store_scrapper.py --update 5`                | Interactively update product ID 5 |
| `python store_scrapper.py --delete 7`                | Delete product ID 7               |
| `python store_scrapper.py --categories`              | List all product categories       |
| `python store_scrapper.py --by-category electronics` | List products in a category       |

> **Note:** POST / PUT / DELETE calls on FakeStoreAPI are **simulated** — the
> server returns a realistic response but does not persist changes.

---

## Product schema

| Field          | Type  | Description                                      |
| -------------- | ----- | ------------------------------------------------ |
| `id`           | int   | Unique product identifier                        |
| `title`        | str   | Product name                                     |
| `price`        | float | Price in USD                                     |
| `category`     | str   | e.g. `electronics`, `jewelery`, `men's clothing` |
| `description`  | str   | Full product description                         |
| `image`        | str   | Image URL                                        |
| `rating.rate`  | float | Average rating (0–5)                             |
| `rating.count` | int   | Number of ratings                                |
| `scraped_at`   | str   | Timestamp added by this tool                     |

---

## Tracking changes over time

Run the scraper periodically (e.g. via cron):

```bash
# Every day at 08:00
0 8 * * * cd /path/to/store_scrapper && python store_scrapper.py -s csv
```

Each CSV/JSON/HDF5 file is a snapshot. Load multiple files in pandas to diff:

```python
import pandas as pd, glob

frames = [pd.read_csv(f) for f in sorted(glob.glob("scraped_data/*.csv"))]
df = pd.concat(frames, ignore_index=True)

# Show price changes for product 1
print(df[df["id"] == 1][["scraped_at", "price", "title"]])
```
