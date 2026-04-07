#!/usr/bin/env python3
"""
store_scrapper.py — FakeStoreAPI scraper & product manager
Usage:
  python store_scrapper.py -s [json|csv|hdf5]          Scrape & store all products
  python store_scrapper.py --get <id>                   Get a single product
  python store_scrapper.py --add                        Add a new product (interactive)
  python store_scrapper.py --update <id>                Update a product (interactive)
  python store_scrapper.py --delete <id>                Delete a product
  python store_scrapper.py --categories                 List all categories
  python store_scrapper.py --by-category <name>         Get products by category
"""

import argparse
import sys
from datetime import datetime

from api_client import FakeStoreClient
from storage import save_products


TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


# ── helpers ──────────────────────────────────────────────────────────────────

def prompt_product_fields(existing: dict = None) -> dict:
    """Interactive prompt to collect product fields. Pre-fills with existing values."""
    print("\nEnter product details (press Enter to keep current value):")
    fields = {}

    def ask(label, key, cast=str):
        current = existing.get(key, "") if existing else ""
        hint = f" [{current}]" if current else ""
        raw = input(f"  {label}{hint}: ").strip()
        if raw:
            fields[key] = cast(raw)
        elif existing and key in existing:
            fields[key] = existing[key]

    ask("Title", "title")
    ask("Price", "price", float)
    ask("Description", "description")
    ask("Image URL", "image")
    ask("Category", "category")
    return fields


# ── commands ─────────────────────────────────────────────────────────────────

def cmd_scrape(client: FakeStoreClient, fmt: str):
    print(f"[{TIMESTAMP}] Fetching all products from FakeStoreAPI …")
    products = client.get_all_products()
    if not products:
        print("No products returned. Aborting.")
        sys.exit(1)

    # Attach scrape timestamp to every record
    for p in products:
        p["scraped_at"] = TIMESTAMP

    out_path = save_products(products, fmt, TIMESTAMP)
    print(f"✔  {len(products)} products saved → {out_path}")


def cmd_get(client: FakeStoreClient, product_id: int):
    product = client.get_product(product_id)
    if not product:
        print(f"Product {product_id} not found.")
        sys.exit(1)
    print(f"\n{'─'*50}")
    for k, v in product.items():
        print(f"  {k:<14}: {v}")
    print(f"{'─'*50}\n")


def cmd_add(client: FakeStoreClient):
    fields = prompt_product_fields()
    if not fields.get("title"):
        print("Title is required.")
        sys.exit(1)
    result = client.add_product(fields)
    print(f"\n✔  Product created with id={result.get('id')}  (fake – not persisted server-side)")


def cmd_update(client: FakeStoreClient, product_id: int):
    existing = client.get_product(product_id)
    if not existing:
        print(f"Product {product_id} not found.")
        sys.exit(1)
    fields = prompt_product_fields(existing)
    result = client.update_product(product_id, fields)
    print(f"\n✔  Product {product_id} updated.")
    for k, v in result.items():
        print(f"  {k:<14}: {v}")


def cmd_delete(client: FakeStoreClient, product_id: int):
    result = client.delete_product(product_id)
    print(f"\n✔  Product {product_id} deleted (fake – not persisted server-side).")
    print(f"  Server returned id={result.get('id')}")


def cmd_categories(client: FakeStoreClient):
    cats = client.get_categories()
    print("\nAvailable categories:")
    for c in cats:
        print(f"  • {c}")


def cmd_by_category(client: FakeStoreClient, category: str):
    products = client.get_products_by_category(category)
    if not products:
        print(f"No products found for category '{category}'.")
        sys.exit(1)
    print(f"\n{len(products)} products in '{category}':\n")
    for p in products:
        print(f"  [{p['id']:>3}] ${p['price']:>8.2f}  {p['title'][:60]}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="store_scrapper.py",
        description="FakeStoreAPI scraper & product manager",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "-s", "--store",
        metavar="FORMAT",
        choices=["json", "csv", "hdf5"],
        help="Scrape all products and store them.\nFormats: json | csv | hdf5",
    )
    parser.add_argument("--get",       metavar="ID",       type=int, help="Get a single product by ID")
    parser.add_argument("--add",       action="store_true",          help="Add a new product (interactive)")
    parser.add_argument("--update",    metavar="ID",       type=int, help="Update a product by ID (interactive)")
    parser.add_argument("--delete",    metavar="ID",       type=int, help="Delete a product by ID")
    parser.add_argument("--categories",action="store_true",          help="List all product categories")
    parser.add_argument("--by-category", metavar="NAME",             help="List products by category name")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Require at least one action
    if not any([
        args.store, args.get, args.add, args.update,
        args.delete, args.categories, args.by_category
    ]):
        parser.print_help()
        sys.exit(0)

    client = FakeStoreClient()

    if args.store:
        cmd_scrape(client, args.store)
    elif args.get:
        cmd_get(client, args.get)
    elif args.add:
        cmd_add(client)
    elif args.update:
        cmd_update(client, args.update)
    elif args.delete:
        cmd_delete(client, args.delete)
    elif args.categories:
        cmd_categories(client)
    elif args.by_category:
        cmd_by_category(client, args.by_category)


if __name__ == "__main__":
    main()
