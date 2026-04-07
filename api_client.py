"""
api_client.py — Thin wrapper around the FakeStoreAPI REST endpoints.

Endpoints used
--------------
GET    /products                    – all products
GET    /products/{id}               – single product
POST   /products                    – create product  (fake, not persisted)
PUT    /products/{id}               – full update     (fake, not persisted)
PATCH  /products/{id}               – partial update  (fake, not persisted)
DELETE /products/{id}               – delete product  (fake, not persisted)
GET    /products/categories         – list categories
GET    /products/category/{name}    – products in a category
"""

from __future__ import annotations

import sys
import time
from typing import Any

import requests

BASE_URL = "https://fakestoreapi.com"
TIMEOUT  = 15          # seconds
RETRIES  = 3
BACKOFF  = 2           # seconds between retries


class FakeStoreClient:
    """Session-based HTTP client for FakeStoreAPI with retry logic."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session  = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept":       "application/json",
        })

    # ── low-level ─────────────────────────────────────────────────────────────

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        for attempt in range(1, RETRIES + 1):
            try:
                resp = self.session.request(
                    method, url, timeout=TIMEOUT, **kwargs
                )
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.HTTPError as exc:
                print(f"  HTTP {exc.response.status_code} on {method} {url}", file=sys.stderr)
                raise
            except requests.exceptions.ConnectionError:
                if attempt < RETRIES:
                    print(f"  Connection error, retrying ({attempt}/{RETRIES}) …", file=sys.stderr)
                    time.sleep(BACKOFF * attempt)
                else:
                    print("  Could not reach FakeStoreAPI. Check your internet connection.", file=sys.stderr)
                    sys.exit(1)
            except requests.exceptions.Timeout:
                print(f"  Request timed out (attempt {attempt}/{RETRIES})", file=sys.stderr)
                if attempt == RETRIES:
                    sys.exit(1)
                time.sleep(BACKOFF)

    # ── products ──────────────────────────────────────────────────────────────

    def get_all_products(self) -> list[dict]:
        """Fetch all products (no server-side pagination on this API)."""
        return self._request("GET", "/products") or []

    def get_product(self, product_id: int) -> dict | None:
        try:
            return self._request("GET", f"/products/{product_id}")
        except requests.exceptions.HTTPError:
            return None

    def add_product(self, payload: dict) -> dict:
        """
        POST /products — FakeStoreAPI does NOT persist the object;
        it returns a fake id (always 21).
        """
        return self._request("POST", "/products", json=payload)

    def update_product(self, product_id: int, payload: dict) -> dict:
        """PUT /products/{id} — full replacement (fake, not persisted)."""
        return self._request("PUT", f"/products/{product_id}", json=payload)

    def patch_product(self, product_id: int, payload: dict) -> dict:
        """PATCH /products/{id} — partial update (fake, not persisted)."""
        return self._request("PATCH", f"/products/{product_id}", json=payload)

    def delete_product(self, product_id: int) -> dict:
        """DELETE /products/{id} — returns the deleted object (fake)."""
        return self._request("DELETE", f"/products/{product_id}")

    # ── categories ────────────────────────────────────────────────────────────

    def get_categories(self) -> list[str]:
        return self._request("GET", "/products/categories") or []

    def get_products_by_category(self, category: str) -> list[dict]:
        return self._request("GET", f"/products/category/{category}") or []
