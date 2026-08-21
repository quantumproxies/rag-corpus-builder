"""Heading-aware Markdown chunking, standard library only.

Sections come first: a Markdown heading is the author's own boundary, and it is
almost always a better split point than "every 900 characters". Only when a
section overflows do we pack its paragraphs into sub-chunks.

Token counts are estimated at 4 characters per token — close enough for budgeting
and honest about being an estimate.
"""
from __future__ import annotations

import hashlib
import re

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
FENCE = re.compile(r"^\s*```")
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def content_hash(text: str) -> str:
    """Hash of whitespace-normalised text — catches the same boilerplate everywhere."""
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().lower().encode()).hexdigest()[:16]


def _sections(markdown: str) -> list[tuple[list[str], str]]:
    """Split into (heading_path, body). Code fences are never split."""
    path: list[str] = []
    current: list[str] = []
    out: list[tuple[list[str], str]] = []
    in_fence = False

    for line in markdown.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
        heading = None if in_fence else HEADING.match(line)
        if heading:
            if current:
                out.append((list(path), "\n".join(current).strip()))
                current = []
            level, title = len(heading.group(1)), heading.group(2).strip()
            path = path[: level - 1] + [title]
        else:
            current.append(line)

    if current:
        out.append((list(path), "\n".join(current).strip()))
    return [(p, b) for p, b in out if b]


def _pack(body: str, target: int) -> list[str]:
    """Pack paragraphs into pieces of roughly `target` tokens."""
    pieces: list[str] = []
    buffer: list[str] = []
    size = 0
    for paragraph in re.split(r"\n{2,}", body):
        cost = estimate_tokens(paragraph)
        if buffer and size + cost > target:
            pieces.append("\n\n".join(buffer))
            buffer, size = [], 0
        buffer.append(paragraph)
        size += cost
    if buffer:
        pieces.append("\n\n".join(buffer))
    return pieces


def chunk(markdown: str, target_tokens: int = 400, min_tokens: int = 40) -> list[dict]:
    """Markdown -> [{text, tokens, heading_path}], sections first, packing second."""
    out: list[dict] = []
    for path, body in _sections(markdown):
        for piece in _pack(body, target_tokens):
            tokens = estimate_tokens(piece)
            if tokens < min_tokens:
                continue
            # Prefix the heading path so a retrieved chunk carries its own context.
            header = " > ".join(path)
            text = f"{header}\n\n{piece}" if header else piece
            out.append({"text": text, "tokens": estimate_tokens(text), "heading_path": path})
    return out
