#!/usr/bin/env python3
"""Query the local Tangshan No.1 High School history vector index."""

from __future__ import annotations

import argparse
import re
import sqlite3
from array import array
from pathlib import Path

from build_index import DEFAULT_DB_PATH, tokenize, vectorize

STOPWORDS = {
    "什么",
    "什么时候",
    "何时",
    "是",
    "的",
    "了",
    "吗",
    "呢",
    "请",
    "一下",
    "根据",
    "校史",
}
FOUNDING_TERMS = ("建立", "成立", "建校", "创办", "设立", "前身", "更名")
FOUNDING_PASSAGE_TERMS = ("前身", "设立", "创办", "学堂", "迄今", "清朝", "新政")
YEAR_RE = re.compile(r"(18|19|20)\d{2}年?")


def decode_vector(blob: bytes) -> list[float]:
    values = array("f")
    values.frombytes(blob)
    return list(values)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def keyword_overlap(query_tokens: set[str], passage_tokens: set[str]) -> float:
    if not query_tokens or not passage_tokens:
        return 0.0
    return len(query_tokens & passage_tokens) / len(query_tokens)


def build_fts_query(question: str) -> str:
    terms: list[str] = []
    for token in tokenize(question):
        if token in STOPWORDS:
            continue
        if len(token.strip()) <= 1:
            continue
        terms.append(token)
    deduped = list(dict.fromkeys(terms))
    if any(term in question for term in FOUNDING_TERMS):
        deduped.extend(["创办", "设立", "前身", "学堂", "迄今"])
        deduped = list(dict.fromkeys(deduped))
    return " OR ".join(deduped[:12])


def founding_bonus(question: str, passage_text: str) -> float:
    if not any(term in question for term in FOUNDING_TERMS):
        return 0.0

    bonus = 0.0
    keyword_hits = sum(1 for term in FOUNDING_PASSAGE_TERMS if term in passage_text)
    if keyword_hits:
        bonus += min(keyword_hits * 0.06, 0.24)
    if keyword_hits and YEAR_RE.search(passage_text):
        bonus += 0.08
    return bonus


def search(question: str, db_path: Path, top_k: int) -> list[dict[str, object]]:
    query_vector = vectorize(question)
    query_tokens = {
        token
        for token in tokenize(question)
        if token not in STOPWORDS and len(token.strip()) > 1
    }
    rows: list[dict[str, object]] = []

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        fts_scores: dict[int, float] = {}
        fts_query = build_fts_query(question)
        if fts_query:
            for row in connection.execute(
                """
                SELECT rowid, bm25(chunks_fts) AS bm25_score
                FROM chunks_fts
                WHERE chunks_fts MATCH ?
                LIMIT ?
                """,
                (fts_query, max(top_k * 8, 40)),
            ):
                fts_scores[row["rowid"]] = 1.0 / (1.0 + abs(row["bm25_score"]))

        for row in connection.execute(
            "SELECT id, page_start, page_end, text, vector FROM chunks"
        ):
            passage_text = row["text"]
            passage_vector = decode_vector(row["vector"])
            dense_score = cosine_similarity(query_vector, passage_vector)
            overlap_score = keyword_overlap(query_tokens, set(tokenize(passage_text)))
            fts_score = fts_scores.get(row["id"], 0.0)
            bonus = founding_bonus(question, passage_text)
            score = dense_score * 0.50 + overlap_score * 0.15 + fts_score * 0.25 + bonus
            rows.append(
                {
                    "id": row["id"],
                    "page_start": row["page_start"],
                    "page_end": row["page_end"],
                    "text": passage_text,
                    "score": score,
                    "dense_score": dense_score,
                    "fts_score": fts_score,
                    "bonus": bonus,
                }
            )
    finally:
        connection.close()

    rows.sort(key=lambda item: item["score"], reverse=True)
    return rows[:top_k]


def format_results(question: str, matches: list[dict[str, object]]) -> str:
    lines: list[str] = []
    lines.append(f"Question: {question}")
    lines.append("")

    if not matches:
        lines.append("No matching passages found.")
        return "\n".join(lines)

    lines.append("Top passages:")
    lines.append("")

    for index, match in enumerate(matches, start=1):
        page_start = match["page_start"]
        page_end = match["page_end"]
        page_label = f"p.{page_start}" if page_start == page_end else f"pp.{page_start}-{page_end}"
        lines.append(
            f"[{index}] score={match['score']:.4f} dense={match['dense_score']:.4f} "
            f"fts={match['fts_score']:.4f} bonus={match['bonus']:.4f} pages={page_label}"
        )
        lines.append(str(match["text"]).strip())
        lines.append("")

    lines.append("Answering guidance:")
    lines.append("- Answer only from the retrieved passages.")
    lines.append("- Keep dates, names, and events aligned with the cited pages.")
    lines.append("- If evidence is incomplete, say that explicitly.")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query the local SQLite vector index for Tangshan No.1 High School history."
    )
    parser.add_argument("question", help="Natural-language question to search.")
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database built by build_index.py.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of passages to return.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = Path(args.db).resolve()
    if not db_path.exists():
        raise FileNotFoundError(
            f"Index not found: {db_path}. Run install.sh first to build the local index."
        )

    matches = search(args.question, db_path, max(1, args.top_k))
    print(format_results(args.question, matches))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
