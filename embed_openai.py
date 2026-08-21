"""Embed a corpus in batches, resumably.

Embedding 50,000 chunks and losing it to a timeout at chunk 48,000 is a rite of
passage nobody needs twice. This writes as it goes and skips ids already present
in the output file.

    pip install openai
    export OPENAI_API_KEY=sk-...
    python3 embed_openai.py corpus.jsonl --out vectors.jsonl --batch 128
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib

from openai import OpenAI


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--model", default=os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small"))
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--out", default="vectors.jsonl")
    args = ap.parse_args()

    records = [json.loads(line) for line in open(args.file, encoding="utf-8") if line.strip()]

    done: set[str] = set()
    out_path = pathlib.Path(args.out)
    if out_path.exists():
        for line in out_path.open(encoding="utf-8"):
            try:
                done.add(json.loads(line)["id"])
            except (json.JSONDecodeError, KeyError):
                continue
        print(f"resuming: {len(done)} already embedded")

    pending = [r for r in records if r["id"] not in done]
    print(f"{len(pending)} chunks to embed with {args.model}")

    client = OpenAI()
    with out_path.open("a", encoding="utf-8") as fh:
        for i in range(0, len(pending), args.batch):
            batch = pending[i:i + args.batch]
            response = client.embeddings.create(model=args.model, input=[r["text"] for r in batch])
            for record, item in zip(batch, response.data):
                fh.write(json.dumps({
                    "id": record["id"],
                    "vector": item.embedding,
                    "source_url": record.get("source_url"),
                    "heading_path": record.get("heading_path"),
                    "text": record["text"],
                }) + "\n")
            fh.flush()
            print(f"  {min(i + args.batch, len(pending))}/{len(pending)}")

    print(f"\n{args.out} ready")


if __name__ == "__main__":
    main()
