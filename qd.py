"""QuanticData calls used by the corpus pipeline."""
from __future__ import annotations

import os
import time
from typing import Any

import requests

BASE = "https://api.quanticdata.io/v1"
_s = requests.Session()


def _h() -> dict[str, str]:
    key = os.environ.get("QUANTICDATA_API_KEY")
    if not key:
        raise SystemExit("set QUANTICDATA_API_KEY — https://app.quanticdata.io/register")
    return {"Authorization": f"Bearer {key}"}


def _payload(r: requests.Response, what: str) -> dict:
    data = r.json()
    if data.get("type") == "error" or not r.ok:
        raise RuntimeError(f"{what} ({r.status_code}): {data.get('message')}")
    return data.get("payload", {})


def map_site(url: str, limit: int = 5000, search: str | None = None) -> dict:
    body: dict[str, Any] = {"url": url, "limit": limit}
    if search:
        body["search"] = search
    return _payload(_s.post(f"{BASE}/map", json=body, headers=_h(), timeout=120), "map")


def batch_scrape(urls: list[str], concurrency: int = 10, poll: float = 3.0) -> list[dict]:
    """Start a batch job and wait it out. Returns the items, errors included."""
    job = _payload(_s.post(f"{BASE}/batch", json={
        "urls": urls, "format": "markdown", "contentMode": "article",
        "concurrency": concurrency,
    }, headers=_h(), timeout=120), "batch")

    job_id = job["id"]
    delay = poll
    while True:
        time.sleep(delay)
        delay = min(delay * 1.3, 20.0)
        status = _payload(_s.get(f"{BASE}/batch/{job_id}", headers=_h(), timeout=60), "batch status")
        print(f"    {status.get('status')}: {status.get('completed')}/{status.get('total')}"
              f" ({status.get('failed')} failed)")
        if status.get("status") in ("completed", "failed", "cancelled"):
            return status.get("items") or []
