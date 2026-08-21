# RAG corpus builder — websites to chunked, de-duplicated, cited JSONL

A pipeline that turns a list of sites into a corpus you can actually embed: map → batch scrape →
Markdown → chunk on headings → de-duplicate by content hash → JSONL with provenance.

Built on the [QuanticData](https://quanticdata.io) Data APIs, so the messy part — rendering,
anti-bot walls, boilerplate stripping — happens server-side and you write pipeline code, not
parser code.

```bash
pip install requests
export QUANTICDATA_API_KEY=qd_live_your_key_here

python3 build.py sites.txt --pattern /docs/ --max-per-site 300 --out corpus.jsonl
python3 inspect_corpus.py corpus.jsonl          # size, duplicates, token histogram
python3 embed_openai.py corpus.jsonl --out vectors.jsonl
```

## Files

| File | What it does |
|---|---|
| [`qd.py`](qd.py) | map / batch / scrape helpers with job polling |
| [`chunker.py`](chunker.py) | heading-aware Markdown chunker, no dependencies |
| [`build.py`](build.py) | the pipeline: sites → filtered URLs → pages → chunks → JSONL |
| [`inspect_corpus.py`](inspect_corpus.py) | corpus stats: tokens, duplicates, thin chunks, per-domain coverage |
| [`embed_openai.py`](embed_openai.py) | batched embeddings with resume, so a crash costs you one batch |

## The record

```jsonc
{ "id": "b7c1…",                       // sha256 of the normalised text
  "text": "…",
  "tokens": 412,
  "source_url": "https://example.com/docs/auth",
  "title": "Authentication",
  "heading_path": ["Docs", "Authentication", "API keys"],
  "domain": "example.com",
  "fetched_at": "2026-08-21T09:14:00Z",
  "chunk_index": 3, "chunk_count": 9 }
```

`heading_path` is the part most corpus builders throw away and then miss. A chunk that says
"rotate it every 90 days" is useless on its own and unambiguous under
`Docs > Authentication > API keys` — and it gives the retriever a second field to match on.

## Design decisions, and why

**Chunk on headings, not on a character count.** Markdown from `/v1/scrape` keeps its `#`
structure, so sections are already the author's own semantic units. `chunker.py` splits on
headings first and only falls back to paragraph packing when a section exceeds the target size.

**De-duplicate on normalised content, not on URL.** The same terms-of-service block appears on
forty pages. Hashing whitespace-normalised text catches it; hashing the URL does not. On a
typical docs crawl this removes 15–30% of chunks — and every one of those is a chunk your
retriever would otherwise return instead of the answer.

**Keep provenance in the record.** `source_url` and `fetched_at` on every chunk are what let you
cite an answer, re-crawl selectively, and expire stale content. Adding them later is a rebuild.

**Filter before you fetch.** `map` is a flat $0.0005 and returns the whole URL list; filtering it
down to `/docs/` before the batch job is the difference between paying for 300 pages and paying
for 4,000. See `--pattern`.

## Cost

Map $0.0005 per site, pages $0.0002 each. A 2,000-page corpus across ten sites is about **$0.41**.
Embeddings will cost you more than the crawl did.

## Related

- [Web Data API for AI](https://quanticdata.io/web-data-api-for-ai/) · [Crawl & Map API](https://quanticdata.io/crawl-map/) · [Web Scraping API](https://quanticdata.io/web-scraping-api/)
- [How to create an LLM dataset](https://quanticdata.io/blog/how-to-create-an-llm-dataset/) · [How to feed data to an LLM](https://quanticdata.io/blog/how-to-feed-data-to-an-llm/)
- [What is web data?](https://quanticdata.io/blog/what-is-web-data/) · [How do data pipelines work?](https://quanticdata.io/blog/how-do-data-pipelines-work/)

MIT licensed.
