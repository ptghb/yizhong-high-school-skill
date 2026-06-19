#!/usr/bin/env python3
"""Build a lightweight local vector index for the Tangshan No.1 High School PDF."""

from __future__ import annotations

import argparse
import hashlib
import logging
import math
import re
import sqlite3
from array import array
from pathlib import Path

import fitz
import jieba

jieba.setLogLevel(logging.ERROR)


DIMENSION = 768
MAX_CHARS = 720
OVERLAP_CHARS = 120

SKILL_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SKILL_DIR.parents[2]
DEFAULT_PDF_PATH = WORKSPACE_ROOT / "唐山市第一中学校史.pdf"
DEFAULT_DB_PATH = SKILL_DIR / "history_index.db"

PUNCTUATION_RE = re.compile(r"[。！？；!?;.]$")
LATIN_RE = re.compile(r"[A-Za-z0-9]+")
CHINESE_BLOCK_RE = re.compile(r"[\u4e00-\u9fff]+")


def normalize_text(text: str) -> str:
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def merge_lines(text: str) -> str:
    paragraphs: list[str] = []
    current: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                paragraphs.append("".join(current).strip())
                current = []
            continue
        current.append(line)
        if PUNCTUATION_RE.search(line):
            paragraphs.append("".join(current).strip())
            current = []

    if current:
        paragraphs.append("".join(current).strip())

    return "\n\n".join(p for p in paragraphs if p)


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    tokens: list[str] = []

    for word in LATIN_RE.findall(lowered):
        tokens.append(word)

    for block in CHINESE_BLOCK_RE.findall(text):
        jieba_tokens = [token.strip() for token in jieba.lcut(block) if token.strip()]
        tokens.extend(jieba_tokens)
        if len(block) > 1:
            tokens.extend(block[i : i + 2] for i in range(len(block) - 1))

    return tokens


def vectorize(text: str, dimension: int = DIMENSION) -> list[float]:
    vector = [0.0] * dimension

    for token in tokenize(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "little") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def encode_vector(vector: list[float]) -> bytes:
    return array("f", vector).tobytes()


def extract_page_texts(pdf_path: Path) -> list[tuple[int, str]]:
    pages: list[tuple[int, str]] = []
    with fitz.open(pdf_path) as document:
        for page_number, page in enumerate(document, start=1):
            raw_text = page.get_text("text", sort=True)
            cleaned = merge_lines(normalize_text(raw_text))
            if cleaned:
                pages.append((page_number, cleaned))
    return pages


def split_chunks(page_number: int, text: str) -> list[dict[str, object]]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: list[dict[str, object]] = []
    current = ""

    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= MAX_CHARS:
            current = candidate
            continue

        if current:
            chunks.append(
                {
                    "page_start": page_number,
                    "page_end": page_number,
                    "text": current.strip(),
                }
            )

        if len(paragraph) <= MAX_CHARS:
            current = paragraph
            continue

        start = 0
        while start < len(paragraph):
            end = min(start + MAX_CHARS, len(paragraph))
            piece = paragraph[start:end].strip()
            if piece:
                chunks.append(
                    {
                        "page_start": page_number,
                        "page_end": page_number,
                        "text": piece,
                    }
                )
            if end >= len(paragraph):
                current = ""
                break
            start = max(end - OVERLAP_CHARS, start + 1)

    if current:
        chunks.append(
            {
                "page_start": page_number,
                "page_end": page_number,
                "text": current.strip(),
            }
        )

    return chunks


def build_index(pdf_path: Path, db_path: Path) -> tuple[int, int]:
    page_texts = extract_page_texts(pdf_path)
    all_chunks: list[dict[str, object]] = []

    for page_number, text in page_texts:
        all_chunks.extend(split_chunks(page_number, text))

    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("DROP TABLE IF EXISTS chunks")
        connection.execute("DROP TABLE IF EXISTS metadata")
        connection.execute(
            """
            CREATE TABLE chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_start INTEGER NOT NULL,
                page_end INTEGER NOT NULL,
                text TEXT NOT NULL,
                search_text TEXT NOT NULL,
                vector BLOB NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE VIRTUAL TABLE chunks_fts USING fts5(
                search_text,
                content='chunks',
                content_rowid='id'
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        for chunk in all_chunks:
            vector = vectorize(chunk["text"])
            search_text = " ".join(tokenize(chunk["text"]))
            cursor = connection.execute(
                """
                INSERT INTO chunks (page_start, page_end, text, search_text, vector)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    chunk["page_start"],
                    chunk["page_end"],
                    chunk["text"],
                    search_text,
                    sqlite3.Binary(encode_vector(vector)),
                ),
            )
            row_id = cursor.lastrowid
            connection.execute(
                "INSERT INTO chunks_fts(rowid, search_text) VALUES (?, ?)",
                (row_id, search_text),
            )

        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            [
                ("pdf_path", str(pdf_path)),
                ("dimension", str(DIMENSION)),
                ("pages", str(len(page_texts))),
                ("chunks", str(len(all_chunks))),
            ],
        )
        connection.commit()
    finally:
        connection.close()

    return len(page_texts), len(all_chunks)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a local SQLite vector index from the Tangshan No.1 High School history PDF."
    )
    parser.add_argument(
        "--pdf",
        default=str(DEFAULT_PDF_PATH),
        help="Path to the source PDF file.",
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="Path to the output SQLite database.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pdf_path = Path(args.pdf).resolve()
    db_path = Path(args.db).resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages, chunks = build_index(pdf_path, db_path)
    print(f"Indexed PDF: {pdf_path}")
    print(f"Pages extracted: {pages}")
    print(f"Chunks stored: {chunks}")
    print(f"SQLite index: {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
