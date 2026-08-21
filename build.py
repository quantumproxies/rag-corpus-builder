"""sites.txt -> corpus.jsonl.

    python3 build.py sites.txt --pattern /docs/ --max-per-site 300 --out corpus.jsonl

sites.txt holds one site per line (any URL on it). --pattern filters the mapped
URL list *before* anything is fetched, which is where the money is saved.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from datetime import datetime, timezone
from urllib.parse import urlparse

from chunker import chunk, content_hash
from qd import batch_scrape, map_site


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sites", type=pathlib.Path)
    ap.add_argument("--pattern", default=None, help="only URLs containing this substring")
    ap.add_argument("--max-per-site", type=int, default=200)
    ap.add_argument("--target-tokens", type=int, default=400)
    ap.add_argument("--batch", type=int, default=200, help="URLs per batch job")
    ap.add_argument("--out", default="corpus.jsonl")
    args = ap.parse_args()

    sites = [ln.strip() for ln in args.sites.read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.startswith("#")]

    seen_hashes: set[str] = set()
    written = duplicates = pages = 0
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with open(args.out, "w", encoding="utf-8") as fh:
        for site in sites:
            print(f"\n{site}")
            mapped = map_site(site, limit=5000, search=args.pattern)
            urls = [u for u in (mapped.get("links") or [])
                    if not args.pattern or args.pattern in u][: args.max_per_site]
            print(f"  {mapped.get('total')} URLs known, {len(urls)} selected "
                  f"(≈ ${0.0005 + len(urls) * 0.0002:.4f})")
            if not urls:
                continue

            for i in range(0, len(urls), args.batch):
                items = batch_scrape(urls[i:i + args.batch])
                for item in items:
                    markdown = item.get("content")
                    if item.get("error") or not markdown:
                        continue
                    pages += 1
                    chunks = chunk(markdown, target_tokens=args.target_tokens)
                    for index, piece in enumerate(chunks):
                        digest = content_hash(piece["text"])
                        if digest in seen_hashes:
                            duplicates += 1
                            continue
                        seen_hashes.add(digest)
                        fh.write(json.dumps({
                            "id": digest,
                            "text": piece["text"],
                            "tokens": piece["tokens"],
                            "source_url": item.get("url"),
                            "title": item.get("title"),
                            "heading_path": piece["heading_path"],
                            "domain": urlparse(item.get("url") or "").netloc.removeprefix("www."),
                            "fetched_at": fetched_at,
                            "chunk_index": index,
                            "chunk_count": len(chunks),
                        }, ensure_ascii=False) + "\n")
                        written += 1

    print(f"\n{pages} pages -> {written} unique chunks "
          f"({duplicates} duplicates dropped) -> {args.out}")


if __name__ == "__main__":
    main()
