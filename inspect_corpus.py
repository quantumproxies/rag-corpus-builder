"""Look at a corpus before you pay to embed it.

Prints the token histogram, per-domain coverage, the thinnest chunks and the
near-duplicate heading paths — the four things that predict bad retrieval.

    python3 inspect_corpus.py corpus.jsonl
"""
from __future__ import annotations

import argparse
import json
from collections import Counter


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    args = ap.parse_args()

    records = [json.loads(line) for line in open(args.file, encoding="utf-8") if line.strip()]
    if not records:
        raise SystemExit("empty corpus")

    tokens = sorted(r.get("tokens", 0) for r in records)
    total = sum(tokens)
    print(f"{len(records):,} chunks, {total:,} estimated tokens "
          f"(median {tokens[len(tokens) // 2]}, max {tokens[-1]})\n")

    buckets = Counter()
    for t in tokens:
        buckets[min(1000, (t // 100) * 100)] += 1
    for lower in sorted(buckets):
        bar = "#" * min(50, buckets[lower] * 50 // max(buckets.values()))
        label = f"{lower}+" if lower == 1000 else f"{lower}-{lower + 99}"
        print(f"  {label:>9} {buckets[lower]:>6}  {bar}")

    print("\nper domain")
    for domain, n in Counter(r.get("domain") for r in records).most_common(15):
        pages = len({r.get("source_url") for r in records if r.get("domain") == domain})
        print(f"  {n:>6} chunks from {pages:>4} pages  {domain}")

    thin = [r for r in records if r.get("tokens", 0) < 60]
    print(f"\n{len(thin)} chunks under 60 tokens (usually navigation leftovers or stubs)")
    for r in thin[:5]:
        print(f"  {r.get('tokens'):>4}  {r.get('source_url')}  {' > '.join(r.get('heading_path') or [])}")

    repeated = Counter(" > ".join(r.get("heading_path") or []) for r in records)
    print("\nheading paths appearing on many pages (candidates for a stop-list)")
    for path, n in repeated.most_common(8):
        if n > 3 and path:
            print(f"  {n:>4}  {path}")


if __name__ == "__main__":
    main()
